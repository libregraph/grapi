# SPDX-License-Identifier: AGPL-3.0-or-later
import glob
import logging
from logging.handlers import QueueListener
from functools import partial
import multiprocessing
import argparse
import os
import os.path
import signal
import sys
import time

import grapi.api.v1 as grapi

import falcon

try:
    from prometheus_client import multiprocess
    from prometheus_client import generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST, Summary, Counter, Gauge
    PROMETHEUS = True
except ImportError:
    PROMETHEUS = False

try:
    import setproctitle
    SETPROCTITLE = True
except ImportError:
    SETPROCTITLE = False

import bjoern

"""
Master Fleet Runner

Instantiates the specified number of Bjoern WSGI server processes,
each taking orders on their own unix socket and passing requests to
the respective WSGI app (rest, notify or metrics).

"""

PID_FILE = '/var/run/kopano/mfr.pid'
PROCESS_NAME = 'kopano-mfr'
SOCKET_PATH = '/var/run/kopano'
WORKERS = 8
METRICS_LISTEN = 'localhost:6060'

# metrics
if PROMETHEUS:
    REQUEST_TIME = Summary('kopano_mfr_request_processing_seconds', 'Time spent processing request', ['method', 'endpoint'])
    EXCEPTION_COUNT = Counter('kopano_mfr_total_unhandled_exceptions', 'Total number of unhandled exceptions')
    MEMORY_GAUGE = Gauge('kopano_mfr_virtual_memory_bytes', 'Virtual memory size in bytes', ['worker'])
    CPUTIME_GAUGE = Gauge('kopano_mfr_cpu_seconds_total', 'Total user and system CPU time spent in seconds', ['worker'])

RUNNING = True


def sigchld(*args):
    global RUNNING
    if RUNNING:
        logging.info('child was terminated, initiate shutdown')
        RUNNING = False


def sigterm(*args):
    global RUNNING
    logging.info('process received shutdown signal')
    RUNNING = False


# TODO use kopano.Service, for config file, pidfile, logging, restarting etc.
def create_pidfile(path):
    try:
        with open(path, 'r') as _file:
            last_pid = int(_file.read())

        # check if pid/name match
        last_process_cmdline = '/proc/%d/cmdline' % last_pid
        with open(last_process_cmdline, 'r') as _file:
            cmdline = _file.read()
            if 'kopano-mfr' in cmdline:
                print('Kopano-mfr is already running..', file=sys.stderr)
                sys.exit(-1)

    except FileNotFoundError:
        pass

    with open(path, 'w') as _file:
        pid = str(os.getpid())
        _file.write(pid)


def opt_args():
    parser = argparse.ArgumentParser(prog=PROCESS_NAME, description='Kopano Grapi Master Fleet Runner')
    parser.add_argument("--socket-path", dest="socket_path",
                        help="parent directory for unix sockets (default: {})".format(SOCKET_PATH),
                        default=SOCKET_PATH)
    parser.add_argument("--pid-file", dest='pid_file', default=PID_FILE,
                        help="pid file location (default: {})".format(PID_FILE), metavar="PATH")
    parser.add_argument("-w", "--workers", dest="workers", type=int, default=WORKERS,
                        help="number of workers (unix sockets)", metavar="N")
    parser.add_argument("--insecure", dest='insecure', action='store_true', default=False,
                        help="allow insecure connections")
    parser.add_argument("--enable-auth-basic", dest='auth_basic', action='store_true', default=False,
                        help="enable basic authentication")
    parser.add_argument("--enable-auth-passthrough", dest='auth_passthrough', action='store_true', default=False,
                        help="enable passthrough authentication (use with caution)")
    parser.add_argument("--disable-auth-bearer", dest='auth_bearer', action='store_false', default=True,
                        help="disable bearer authentication")
    parser.add_argument("--with-metrics", dest='with_metrics', action='store_true', default=False,
                        help="enable metrics process")
    parser.add_argument("--metrics-listen", dest='metrics_listen', metavar='ADDRESS:PORT',
                        default=METRICS_LISTEN, help="metrics process address")
    parser.add_argument("--process-name", dest='process_name',
                        default=PROCESS_NAME, help="set process name", metavar="NAME")
    parser.add_argument("--backends", dest='backends', default='kopano',
                        help="backends to enable (comma-separated)", metavar="LIST")
    parser.add_argument("--enable-experimental-endpoints", dest='with_experimental', action='store_true', default=False, help="enable API endpoints which are considered experimental")

    return parser.parse_args()


def error_handler(ex, req, resp, params, with_metrics):
    if not isinstance(ex, (falcon.HTTPError, falcon.HTTPStatus)):
        if with_metrics:
            if PROMETHEUS:
                EXCEPTION_COUNT.inc()
        logging.exception('unhandled exception while processing request', exc_info=ex)
        raise falcon.HTTPError(falcon.HTTP_500)
    raise ex

# falcon metrics middleware


class FalconMetrics(object):
    def process_request(self, req, resp):
        req.context['start_time'] = time.time()

    def process_resource(self, req, resp, resource, params):
        req.context['label'] = \
            req.uri_template.replace('{method}', params.get('method', ''))

    def process_response(self, req, resp, resource):
        t = time.time() - req.context['start_time']
        label = req.context.get('label')
        if label:
            if 'deltaid' in req.context:
                label = label.replace(req.context['deltaid'], 'delta')
            REQUEST_TIME.labels(req.method, label).observe(t)


def collect_worker_metrics(workers):
    ticks = 100.0
    try:
        ticks = os.sysconf('SC_CLK_TCK')
    except (ValueError, TypeError, AttributeError):
        pass

    for worker in workers:
        name, pid = worker
        with open('/proc/{}/stat'.format(pid), 'rb') as stat:
            parts = stat.read().split()
            MEMORY_GAUGE.labels(name).set(float(parts[23]))
            utime = float(parts[13]) / ticks
            stime = float(parts[14]) / ticks
            CPUTIME_GAUGE.labels(name).set(utime + stime)


# Expose metrics.
def metrics_app(workers, environ, start_response):
    collect_worker_metrics(workers)
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    data = generate_latest(registry)
    status = '200 OK'
    response_headers = [
        ('Content-type', CONTENT_TYPE_LATEST),
        ('Content-Length', str(len(data)))
    ]
    start_response(status, response_headers)
    return iter([data])


# TODO merge run_*
def run_app(socket_path, n, options):
    signal.signal(signal.SIGINT, lambda *args: 0)
    if SETPROCTITLE:
        setproctitle.setproctitle('%s rest %d' % (options.process_name, n))
    if options.with_metrics:
        middleware = [FalconMetrics()]
    else:
        middleware = None
    backends = options.backends.split(',')
    app = grapi.RestAPI(options=options, middleware=middleware, backends=backends)
    handler = partial(error_handler, with_metrics=options.with_metrics)
    app.add_error_handler(Exception, handler)
    unix_socket = 'unix:' + os.path.join(socket_path, 'rest%d.sock' % n)
    logging.info('starting rest worker: %s', unix_socket)
    bjoern.run(app, unix_socket)


def run_notify(socket_path, options):
    signal.signal(signal.SIGINT, lambda *args: 0)
    if SETPROCTITLE:
        setproctitle.setproctitle('%s notify' % options.process_name)
    if options.with_metrics:
        middleware = [FalconMetrics()]
    else:
        middleware = None
    backends = options.backends.split(',')
    app = grapi.NotifyAPI(options=options, middleware=middleware, backends=backends)
    handler = partial(error_handler, with_metrics=options.with_metrics)
    app.add_error_handler(Exception, handler)
    unix_socket = 'unix:' + os.path.join(socket_path, 'notify.sock')
    logging.info('starting notify worker: %s', unix_socket)
    bjoern.run(app, unix_socket)


def run_metrics(socket_path, options, workers):
    signal.signal(signal.SIGINT, lambda *args: 0)
    if SETPROCTITLE:
        setproctitle.setproctitle('%s metrics' % options.process_name)
    address = options.metrics_listen
    logging.info('starting metrics worker: %s', address)
    address = address.split(':')
    bjoern.run(partial(metrics_app, workers), address[0], int(address[1]))


def logger_init():
    q = multiprocessing.Queue()
    # this is the handler for all log records
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(asctime)s - %(process)s - %(message)s"))

    # ql gets records from the queue and sends them to the handler
    ql = QueueListener(q, handler)
    ql.start()

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # add the handler to the logger so records from this process are handled
    logger.addHandler(handler)

    return ql, q


def main():
    global RUNNING

    args = opt_args()

    if SETPROCTITLE:
        setproctitle.setproctitle(args.process_name + ' master')

    create_pidfile(args.pid_file)

    for f in glob.glob(os.path.join(args.socket_path, 'rest*.sock')):
        os.unlink(f)
    for f in glob.glob(os.path.join(args.socket_path, 'notify*.sock')):
        os.unlink(f)

    q_listener, q = logger_init()
    logging.info('starting kopano-mfr')

    workers = []
    for n in range(args.workers):
        process = multiprocessing.Process(target=run_app, name='rest{}'.format(n), args=(args.socket_path, n, args))
        workers.append(process)

    notify_process = multiprocessing.Process(target=run_notify, name='notify', args=(args.socket_path, args))
    workers.append(notify_process)

    for worker in workers:
        worker.daemon = True
        worker.start()

    if args.with_metrics:
        if PROMETHEUS:
            if not os.environ.get('prometheus_multiproc_dir'):
                logging.error('please export "prometheus_multiproc_dir"')
                sys.exit(-1)

            # Spawn the metrics process later, so we can pass along worker name and pids.
            monitor_workers = [(worker.name, worker.pid) for worker in workers]
            # Include master process.
            monitor_workers.append(('master', os.getpid()))
            metrics_process = multiprocessing.Process(target=run_metrics, args=(args.socket_path, args, monitor_workers))
            metrics_process.daemon = True
            metrics_process.start()
            workers.append(metrics_process)
        else:
            logging.error('please install prometheus client python bindings')
            sys.exit(-1)

    signal.signal(signal.SIGCHLD, sigchld)
    signal.signal(signal.SIGTERM, sigterm)

    try:
        while RUNNING:
            signal.pause()
    except KeyboardInterrupt:
        RUNNING = False
        logging.info('keyboard interrupt')

    logging.info('starting shutdown')

    for worker in workers:
        worker.terminate()
        worker.join()

    q_listener.stop()

    sockets = []
    for n in range(args.workers):
        sockets.append('rest%d.sock' % n)
    sockets.append('notify.sock')
    for socket in sockets:
        try:
            unix_socket = os.path.join(args.socket_path, socket)
            os.unlink(unix_socket)
        except OSError:
            pass

    if args.with_metrics:
        for worker in workers:
            multiprocess.mark_process_dead(worker.pid)

    logging.info('shutdown complete')

if __name__ == '__main__':
    main()
