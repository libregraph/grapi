# SPDX-License-Identifier: AGPL-3.0-or-later
import glob
import logging
from functools import partial
import multiprocessing
import argparse
import errno
import os
import os.path
import signal
import sys
import threading
import time

import grapi.api.v1 as grapi

import bjoern
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

try:
    import colorlog
    COLORLOG = True
except ImportError:
    COLORLOG = False

PROFILE_DIR = os.getenv('PROFILE_DIR')
if PROFILE_DIR:
    if os.path.exists(PROFILE_DIR):
        print("Writing profiles (on exit) to '{}' ...".format(PROFILE_DIR))
        import yappi
    else:
        print("PROFILE_DIR '{}' is invalid, not enabling profiling".format(PROFILE_DIR))
        PROFILE_DIR = None

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
ABNORMAL_SHUTDOWN = False


def sigchld(*args):
    global RUNNING
    global ABNORMAL_SHUTDOWN
    if RUNNING:
        try:
            logging.critical('child was terminated unexpectedly, initiating abnormal shutdown')
        except Exception:
            pass
        RUNNING = False
        ABNORMAL_SHUTDOWN = True


def sigterm(*args):
    global RUNNING
    try:
        logging.info('process received shutdown signal')
    except Exception:
        pass
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
                        type=is_path,
                        default=SOCKET_PATH)
    parser.add_argument("--pid-file", dest='pid_file', default=PID_FILE,
                        help="pid file location (default: {})".format(PID_FILE), metavar="PATH")
    parser.add_argument("--log-level", dest='log_level', default='INFO',
                        help="log level (default: INFO)")
    parser.add_argument("-w", "--workers", dest="workers", type=int, default=WORKERS,
                        help="number of workers (unix sockets)", metavar="N")
    parser.add_argument("--insecure", dest='insecure', action='store_true', default=False,
                        help="allow insecure operations")
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


def is_path(path):
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError("is_path:{} is not a valid path".format(path))
    if not os.access(path, os.W_OK):
        raise argparse.ArgumentTypeError("is_path:{} is not a writeable path".format(path))
    return path


def error_handler(ex, req, resp, params, with_metrics):
    if not isinstance(ex, (falcon.HTTPError, falcon.HTTPStatus)):
        if with_metrics:
            if PROMETHEUS:
                EXCEPTION_COUNT.inc()
        logging.exception('unhandled exception while processing request', exc_info=ex)
        raise falcon.HTTPError(falcon.HTTP_500)
    raise ex


class FalconLabel:
    def process_resource(self, req, resp, resource, params):
        label = req.uri_template.replace('method', params.get('method', ''))
        label = label.replace('/', '_')
        req.context['label'] = label


class FalconMetrics:
    def process_request(self, req, resp):
        req.context['start_time'] = time.time()

    def process_response(self, req, resp, resource):
        t = time.time() - req.context['start_time']
        label = req.context.get('label')
        if label:
            deltaid = req.context.get('deltaid')
            if deltaid:
                label = label.replace(deltaid, 'delta')
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


class Runner:
    def __init__(self, queue, worker, name, process_name, n):
        self.queue = queue
        self.worker = worker
        self.name = name
        self.process_name = process_name
        self.n = n

    def run(self, *args, **kwargs):
        signal.signal(signal.SIGTERM, lambda *args: 0)
        signal.signal(signal.SIGINT, lambda *args: 0)

        if SETPROCTITLE:
            setproctitle.setproctitle('%s %s %d' % (self.process_name, self.name, self.n))

        if PROFILE_DIR:
            yappi.start(builtins=False, profile_threads=True)

        # Start in thread, to allow proper termination, without killing the process.
        thread = threading.Thread(target=self.start, name='%s%d' % (self.name, self.n), args=args, kwargs=kwargs, daemon=True)
        thread.start()
        self.queue.join()
        logging.debug('shutdown %s %d worker with pid %s is complete', self.name, self.n, os.getpid())
        self.stop()
        # NOTE(longsleep): We do not wait on the thread. The process will
        # terminate and also kill the thread. We have no real control on when
        # to shutdown bjoern.run properly.

    def start(self, *args, **kwargs):
        try:
            self.worker(*args, **kwargs)
        except Exception:
            logging.critical('error in %s %d worker with pid %s', self.name, self.n, os.getpid(), exc_info=True)
            self.queue.task_done()  # Mark queue as done, to indicate exit.

    def stop(self, *args, **kwargs):
        if PROFILE_DIR:
            yappi.stop()
            stats = yappi.convert2pstats(yappi.get_func_stats().get())
            stats.dump_stats('{}/{}{}.prof'.format(PROFILE_DIR, self.name, self.n))
            logging.info("dumped profile of %s %d worker", self.name, self.n)


def run_rest(socket_path, n, options):
    middleware = [FalconLabel()]
    if options.with_metrics:
        middleware.append(FalconMetrics())
    backends = options.backends.split(',')
    app = grapi.RestAPI(options=options, middleware=middleware, backends=backends)
    handler = partial(error_handler, with_metrics=options.with_metrics)
    app.add_error_handler(Exception, handler)
    unix_socket = 'unix:' + os.path.join(socket_path, 'rest%d.sock' % n)
    logging.debug('starting rest %d worker (%s) with pid %d', n, unix_socket, os.getpid())
    bjoern.run(app, unix_socket)


def run_notify(socket_path, n, options):
    middleware = [FalconLabel()]
    if options.with_metrics:
        middleware.append(FalconMetrics())
    backends = options.backends.split(',')
    app = grapi.NotifyAPI(options=options, middleware=middleware, backends=backends)
    handler = partial(error_handler, with_metrics=options.with_metrics)
    app.add_error_handler(Exception, handler)
    unix_socket = 'unix:' + os.path.join(socket_path, 'notify%d.sock' % n)
    logging.debug('starting notify %d worker (%s) with pid %d', n, unix_socket, os.getpid())
    bjoern.run(app, unix_socket)


def run_metrics(socket_path, options, workers):
    address = options.metrics_listen
    logging.debug('starting metrics worker (%s) with pid %d', address, os.getpid())
    address_parts = address.split(':')
    bjoern.run(partial(metrics_app, workers),  address_parts[0], int(address_parts[1]))


def init_logging(log_level, log_timestamp=True):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)

    fmt = '%(threadName)-10s[%(process)5d] %(levelname)-8s %(message)s'
    if log_timestamp:
        fmt = '%(asctime)s ' + fmt

    # This is the handler for all log records.
    if COLORLOG:
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s' + fmt))
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(numeric_level)
    # Add the handler to the logger so records from this process are handled.
    root.addHandler(handler)


def main():
    global RUNNING
    global ABNORMAL_SHUTDOWN

    args = opt_args()

    threading.currentThread().setName('master')
    if SETPROCTITLE:
        setproctitle.setproctitle(args.process_name + ' master %s' % ' '.join(sys.argv[1:]))

    create_pidfile(args.pid_file)

    for f in glob.glob(os.path.join(args.socket_path, 'rest*.sock')):
        os.unlink(f)
    for f in glob.glob(os.path.join(args.socket_path, 'notify*.sock')):
        os.unlink(f)

    init_logging(args.log_level)
    logging.info('starting kopano-mfr')

    # Fake exit queue.
    queue = multiprocessing.JoinableQueue(1)
    queue.put(True)

    workers = []
    for n in range(args.workers):
        rest_runner = Runner(queue, run_rest, 'rest', args.process_name, n)
        rest_process = multiprocessing.Process(target=rest_runner.run, name='rest{}'.format(n), args=(args.socket_path, n, args))
        workers.append(rest_process)
        notify_runner = Runner(queue, run_notify, 'notify', args.process_name, n)
        notify_process = multiprocessing.Process(target=notify_runner.run, name='notify{}'.format(n), args=(args.socket_path, n, args))
        workers.append(notify_process)

    for worker in workers:
        worker.daemon = True
        worker.start()

    if args.insecure:
        logging.warn('insecure mode - TLS client connections are are susceptible to man-in-the-middle attacks and safety checks are off - this is not suitable for production use')

    if args.with_experimental:
        logging.warn('experimental endpoints are enabled')

    if args.with_metrics:
        if PROMETHEUS:
            if not os.environ.get('prometheus_multiproc_dir'):
                logging.error('please export "prometheus_multiproc_dir"')
                sys.exit(-1)

            # Spawn the metrics process later, so we can pass along worker name and pids.
            monitor_workers = [(worker.name, worker.pid) for worker in workers]
            # Include master process.
            monitor_workers.append(('master', os.getpid()))
            metrics_runner = Runner(queue, run_metrics, 'metrics', args.process_name, 0)
            metrics_process = multiprocessing.Process(target=metrics_runner.run, args=(args.socket_path, args, monitor_workers))
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

    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    if not ABNORMAL_SHUTDOWN:
        # Flush queue, to tell workers to cleanly exit.
        queue.get()
        try:
            queue.task_done()
        except ValueError:
            # NOTE(longsleep): If a process encountered an error taks_done() was
            # already called, thus it errors which is ok and can be ignored.
            pass

    # Wait for workers to exit.
    deadline = time.monotonic() + 5
    done = []
    while deadline > time.monotonic():
        ready = multiprocessing.connection.wait([worker.sentinel for worker in workers if worker.sentinel not in done], timeout=1)
        done.extend(ready)
        if len(done) == len(workers):
            break

    # Kill off workers which did not exit.
    kill = len(done) != len(workers)
    for worker in workers:
        if kill and worker.is_alive():
            if ABNORMAL_SHUTDOWN:
                logging.critical('killing worker: %d', worker.pid)
                os.kill(worker.pid, signal.SIGKILL)
            else:
                logging.warn('terminating worker: %d', worker.pid)
                worker.terminate()
        multiprocess.mark_process_dead(worker.pid)
        worker.join()

    # Cleanup potentially left over sockets.
    sockets = []
    for n in range(args.workers):
        sockets.append('rest%d.sock' % n)
    for n in range(args.workers):
        sockets.append('notify%d.sock' % n)
    for socket in sockets:
        try:
            unix_socket = os.path.join(args.socket_path, socket)
            os.unlink(unix_socket)
        except OSError as err:
            if err.errno != errno.ENOENT:
                logging.warn('failed to remove socket %s on shutdown, error: %s', unix_socket, err)

    logging.info('shutdown complete')


if __name__ == '__main__':
    main()
