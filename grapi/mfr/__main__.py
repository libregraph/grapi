# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import os
import os.path

from grapi.mfr import Server

# Defaults
PROCESS_NAME = 'kopano-mfr'
SOCKET_PATH = '/var/run/kopano'
WORKERS = 8
METRICS_LISTEN = 'localhost:6060'
TRANSLATIONS_PATH = '/usr/share/kopano-grapi/i18n'


def opt_args():
    parser = argparse.ArgumentParser(prog=PROCESS_NAME, description='Kopano Grapi Master Fleet Runner')
    parser.add_argument("--socket-path", dest="socket_path",
                        help="parent directory for unix sockets (default: {})".format(SOCKET_PATH),
                        type=is_writable_path,
                        default=SOCKET_PATH)
    parser.add_argument("--pid-file", dest='pid_file', help=argparse.SUPPRESS)
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
    parser.add_argument("--translations-path", dest='translations_path', default=TRANSLATIONS_PATH, type=is_path,
                        help="path to translations base folder (default: {}".format(TRANSLATIONS_PATH))

    return parser.parse_args()


def is_writable_path(path, checkWriteable=True):
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError("is_path:{} is not a valid path".format(path))
    if checkWriteable and not os.access(path, os.W_OK):
        raise argparse.ArgumentTypeError("is_path:{} is not a writeable path".format(path))
    return path


def is_path(path):
    return is_writable_path(path, checkWriteable=False)


def main(args=None):
    """The main routine."""
    if args is None:
        args = opt_args()

    server = Server()
    server.serve(args)


if __name__ == '__main__':
    main()
