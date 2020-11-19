# SPDX-License-Identifier: AGPL-3.0-or-later
import errno
import gettext
import glob
import io
import logging
import multiprocessing
import os
import os.path
import signal
import socket
import sys
import threading
import time
import warnings
from functools import partial

import bjoern
import falcon

import grapi.api.v1 as grapi
from grapi.mfr.msgfmt import Msgfmt, PoSyntaxError
from grapi.mfr.utils import parse_accept_language

try:
    import ujson  # noqa: F401
    UJSON = True
except ImportError:
    UJSON = False

try:
    from prometheus_client import (CONTENT_TYPE_LATEST, CollectorRegistry,
                                   Counter, Gauge, Summary, generate_latest)
    from prometheus_client import multiprocess as prometheus_multiprocess
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

WITH_YAPPI = False
WITH_CPROFILE = False
PROFILE_MODE = os.getenv('PROFILE_MODE', None)  # One in [full, request]
PROFILE_DIR = os.getenv('PROFILE_DIR')
if PROFILE_DIR:
    if os.path.exists(PROFILE_DIR):
        if PROFILE_MODE == 'request':
            print("Writing request profiles to '{}' ...".format(PROFILE_DIR))
            import cProfile
            WITH_CPROFILE = True
        else:
            print("Writing profiles (on exit) to '{}' ...".format(PROFILE_DIR))
            import yappi
            WITH_YAPPI = True
    else:
        print("PROFILE_DIR '{}' is invalid, not enabling profiling".format(PROFILE_DIR))
        PROFILE_DIR = None

"""
Master Fleet Runner

Instantiates the specified number of Bjoern WSGI server processes,
each taking orders on their own unix socket and passing requests to
the respective WSGI app (rest, notify or metrics).

"""

# metrics
if PROMETHEUS:
    REQUEST_TIME = Summary('kopano_mfr_request_processing_seconds', 'Time spent processing request', ['method', 'endpoint'])
    EXCEPTION_COUNT = Counter('kopano_mfr_total_unhandled_exceptions', 'Total number of unhandled exceptions')
    MEMORY_GAUGE = Gauge('kopano_mfr_virtual_memory_bytes', 'Virtual memory size in bytes', ['worker'])
    CPUTIME_GAUGE = Gauge('kopano_mfr_cpu_seconds_total', 'Total user and system CPU time spent in seconds', ['worker'])


def error_handler(ex, req, resp, params, with_metrics):
    if not isinstance(ex, (falcon.HTTPError, falcon.HTTPStatus)):
        if with_metrics:
            if PROMETHEUS:
                EXCEPTION_COUNT.inc()
        logging.exception('unhandled exception while processing request', exc_info=ex)
        raise falcon.HTTPError(status=falcon.HTTP_500)
    raise ex


nullTranslations = gettext.NullTranslations(None)


class FalconLabel:
    def __init__(self, translations=None):
        self.translations = translations

    def get_language(self, lang):
        return self.translations.get(lang, nullTranslations.gettext)

    def process_resource(self, req, resp, resource, params):
        label = req.uri_template.replace('method', params.get('method', ''))
        label = label.replace('/', '_')
        req.context.label = label

        if not self.translations:
            req.context.i18n = nullTranslations
            return

        # Set language based on three settings in order:
        # - MailboxSettings
        # - HTTP ACCEPT-LANGUAGE Headers
        # - ?ui_locales parameter

        # The language is selected based on the three options and what languages are available,
        # - when de-at is requested and not available, pick de (if available)
        # - auto fallback to en-gb

        # HTTP ACCEPT-LANGUAGE
        accept_lang = req.headers.get('ACCEPT-LANGUAGE')
        #logging.debug("requesting accept-lang '%s'", accept_lang)
        if accept_lang:
            for lang, _ in parse_accept_language(accept_lang):
                translation = self.translations.get(lang)
                if translation:
                    req.context.i18n = translation
                    #logging.debug("using translation '%s'", lang)
                    return

        req.context.i18n = nullTranslations


class FalconMetrics:
    def process_request(self, req, resp):
        req.context.start_time = time.time()

    def process_response(self, req, resp, resource, req_succeeded=True):
        label = req.context.get("label")
        if label:
            t = time.time() - req.context.start_time
            deltaid = req.context.get('deltaid')
            if deltaid:
                label = label.replace(deltaid, 'delta')
            REQUEST_TIME.labels(req.method, label).observe(t)


class FalconRequestProfiler:
    def process_request(self, req, resp):
        profile = cProfile.Profile()
        profile.enable()
        req.context.profile = profile

    def process_resource(self, req, resp, resource, params):
        pass

    def process_response(self, req, resp, resource, req_succeeded=True):
        profile = req.context.profile
        profile.disable()
        label = req.context.label
        profile.dump_stats('{}/{}.prof'.format(PROFILE_DIR, label))


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
    prometheus_multiprocess.MultiProcessCollector(registry)
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

        if WITH_YAPPI and PROFILE_DIR:
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
        if WITH_YAPPI and PROFILE_DIR:
            yappi.stop()
            stats = yappi.convert2pstats(yappi.get_func_stats().get())
            stats.dump_stats('{}/{}{}.prof'.format(PROFILE_DIR, self.name, self.n))
            logging.info("dumped profile of %s %d worker", self.name, self.n)


class Server:
    def __init__(self):
        self.running = True
        self.abnormal_shutdown = False

    def create_socket_and_listen(self, socket_path):
        sock = socket.socket(socket.AF_UNIX)
        sock.bind(socket_path)
        sock.setblocking(False)
        sock.listen(socket.SOMAXCONN)

        return sock

    def run_rest(self, socket_path, n, options):
        middleware = [FalconLabel(self.translations)]
        if options.with_metrics:
            middleware.append(FalconMetrics())
        if WITH_CPROFILE and PROFILE_DIR:
            middleware.append(FalconRequestProfiler())
        backends = options.backends.split(',')
        app = grapi.RestAPI(options=options, middleware=middleware, backends=backends)
        handler = partial(error_handler, with_metrics=options.with_metrics)
        app.add_error_handler(Exception, handler)
        unix_socket_path = os.path.join(socket_path, 'rest%d.sock' % n)

        # Run server, this blocks.
        logging.debug('starting rest %d worker (unix:%s) with pid %d', n, unix_socket_path, os.getpid())
        bjoern.server_run(self.create_socket_and_listen(unix_socket_path), app)

    def run_notify(self, socket_path, n, options):
        middleware = [FalconLabel(self.translations)]
        if options.with_metrics:
            middleware.append(FalconMetrics())
        if PROFILE_DIR and PROFILE_MODE == 'request':
            middleware.append(FalconRequestProfiler())
        backends = options.backends.split(',')
        app = grapi.NotifyAPI(options=options, middleware=middleware, backends=backends)
        handler = partial(error_handler, with_metrics=options.with_metrics)
        app.add_error_handler(Exception, handler)
        unix_socket_path = os.path.join(socket_path, 'notify%d.sock' % n)

        # Run server, this blocks.
        logging.debug('starting notify %d worker (unix:%s) with pid %d', n, unix_socket_path, os.getpid())
        bjoern.server_run(self.create_socket_and_listen(unix_socket_path), app)

    def run_metrics(self, socket_path, options, workers):
        address = options.metrics_listen

        address_parts = address.split(':')

        # Run server, this blocks.
        logging.debug('starting metrics worker (%s) with pid %d', address, os.getpid())
        bjoern.run(partial(metrics_app, workers), address_parts[0], int(address_parts[1]))

    def init_logging(self, log_level, log_timestamp=True):
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

        # Send all warnings to logging.
        logging.captureWarnings(True)

    def get_translations(self, translations_path):
        translations = {
            'en': gettext.NullTranslations(None),  # Always add default (built-in language en).
        }

        for entry in os.scandir(translations_path):
            if not entry.name.endswith('.po'):
                continue

            pofile = os.path.join(translations_path, entry.name)
            language = os.path.basename(pofile).replace('.po', '')

            # Verify that the language is valid 'de' or 'de-DE'
            if len(language) != 2 and len(language) != 5:
                logging.error("invalid po file with unsupported language '%s' found, skipping", language)
                continue

            try:
                msgfmt = Msgfmt(open(pofile, 'rb'))
            except IOError:
                logging.warning("error when opening po file '%s'", pofile)

            try:
                gnutranslation = gettext.GNUTranslations(io.BytesIO(msgfmt.get()))
            except PoSyntaxError:
                logging.warning("unable to parse po file '%s'", pofile)

            translations[language] = gnutranslation

        return translations

    def serve(self, args):
        threading.currentThread().setName('master')
        if SETPROCTITLE:
            setproctitle.setproctitle(args.process_name + ' master %s' % ' '.join(sys.argv[1:]))

        # Initialize logging, keep this at the beginning!
        self.init_logging(args.log_level)

        for f in glob.glob(os.path.join(args.socket_path, 'rest*.sock')):
            os.unlink(f)
        for f in glob.glob(os.path.join(args.socket_path, 'notify*.sock')):
            os.unlink(f)

        # Initialize translations
        self.translations = self.get_translations(args.translations_path)

        if not self.translations:
            logging.warning('no po files found, no translations will be available')
        else:
            # TODO: lazy-logging, info message?
            logging.debug("translations available for: '%s'", ', '.join(self.translations.keys()))

        if not UJSON:
            warnings.warning('ujson module is not available, falling back to slower stdlib json implementation')

        logging.info('starting kopano-mfr')

        # Fake exit queue.
        queue = multiprocessing.JoinableQueue(1)
        queue.put(True)

        workers = []
        for n in range(args.workers):
            rest_runner = Runner(queue, self.run_rest, 'rest', args.process_name, n)
            rest_process = multiprocessing.Process(target=rest_runner.run, name='rest{}'.format(n), args=(args.socket_path, n, args))
            workers.append(rest_process)
            notify_runner = Runner(queue, self.run_notify, 'notify', args.process_name, n)
            notify_process = multiprocessing.Process(target=notify_runner.run, name='notify{}'.format(n), args=(args.socket_path, n, args))
            workers.append(notify_process)

        for worker in workers:
            worker.daemon = True
            worker.start()

        if args.insecure:
            logging.warning('insecure mode - TLS client connections are susceptible to man-in-the-middle attacks and safety checks are off - this is not suitable for production use')

        if args.with_experimental:
            logging.warning('experimental endpoints are enabled')

        if args.with_metrics:
            if PROMETHEUS:
                if os.environ.get('prometheus_multiproc_dir'):
                    # Spawn the metrics process later, so we can pass along worker name and pids.
                    monitor_workers = [(worker.name, worker.pid) for worker in workers]
                    # Include master process.
                    monitor_workers.append(('master', os.getpid()))
                    metrics_runner = Runner(queue, self.run_metrics, 'metrics', args.process_name, 0)
                    metrics_process = multiprocessing.Process(target=metrics_runner.run, args=(args.socket_path, args, monitor_workers))
                    metrics_process.daemon = True
                    metrics_process.start()
                    workers.append(metrics_process)
                else:
                    logging.error('please export "prometheus_multiproc_dir"')
                    self.running = False
            else:
                logging.error('please install prometheus client python bindings')
                self.running = False

        signal.signal(signal.SIGCHLD, self.sigchld)
        signal.signal(signal.SIGTERM, self.sigterm)

        try:
            while self.running:
                signal.pause()
        except KeyboardInterrupt:
            self.running = False
            logging.info('keyboard interrupt')

        logging.info('starting shutdown')

        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

        if not self.abnormal_shutdown:
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
                if self.abnormal_shutdown:
                    logging.critical('killing worker: %d', worker.pid)
                    os.kill(worker.pid, signal.SIGKILL)
                else:
                    logging.warning('terminating worker: %d', worker.pid)
                    worker.terminate()
            if os.environ.get('prometheus_multiproc_dir') and args.with_metrics and PROMETHEUS:
                prometheus_multiprocess.mark_process_dead(worker.pid)
            worker.join()

        # Cleanup potentially left over sockets.
        sockets = []
        for n in range(args.workers):
            sockets.append('rest%d.sock' % n)
        for n in range(args.workers):
            sockets.append('notify%d.sock' % n)
        for socket in sockets:  # noqa: F402
            try:
                unix_socket = os.path.join(args.socket_path, socket)
                os.unlink(unix_socket)
            except OSError as err:
                if err.errno != errno.ENOENT:
                    logging.warning('failed to remove socket %s on shutdown, error: %s', unix_socket, err)

        logging.info('shutdown complete')

    def sigchld(self, *args):
        if self.running:
            try:
                logging.critical('child was terminated unexpectedly, initiating abnormal shutdown')
            except Exception:
                pass
            self.running = False
            self.abnormal_shutdown = True

    def sigterm(self, *args):
        try:
            logging.info('process received shutdown signal')
        except Exception:
            pass
        self.running = False
