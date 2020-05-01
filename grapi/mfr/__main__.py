# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import os
import os.path

from grapi.mfr import Server


# Defaults
PID_FILE = '/var/run/kopano/mfr.pid'
PROCESS_NAME = 'kopano-mfr'
SOCKET_PATH = '/var/run/kopano'
WORKERS = 8
METRICS_LISTEN = 'localhost:6060'
TRANSLATION_DIR = '/usr/share/kopano-grapi/i18n'


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
    parser.add_argument("--translations-dir", dest='translation_dir', default=TRANSLATION_DIR, type=is_path,
                        help="the directory where translations are (default: {}".format(TRANSLATION_DIR))

    return parser.parse_args()


def is_path(path):
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError("is_path:{} is not a valid path".format(path))
    if not os.access(path, os.W_OK):
        raise argparse.ArgumentTypeError("is_path:{} is not a writeable path".format(path))
    return path


if __name__ == '__main__':
    server = Server()
    server.serve(opt_args())
