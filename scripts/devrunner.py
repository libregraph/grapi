#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import multiprocessing
from wsgiref.simple_server import make_server

from grapi.api.v1 import RestAPI
from grapi.api.v1 import NotifyAPI

REST_PORT=8000
NOTIFY_PORT=8001
BACKEND = ['kopano']

parser = argparse.ArgumentParser(description='grapi development runner')
parser.add_argument('--rest-port', type=int, default=REST_PORT, help='the rest api port (default: {})'.format(REST_PORT))
parser.add_argument('--notify-port', type=int, default=NOTIFY_PORT, help='the notify api port (default: {})'.format(NOTIFY_PORT))
parser.add_argument('--backends', type=str,nargs='+', default=BACKEND, help='backends to enable (space-seperated) (default: {})'.format(BACKEND))
args = parser.parse_args()


def run_rest():
    make_server('localhost', args.rest_port, RestAPI(backends=args.backends)).serve_forever()

def run_notify():
    make_server('localhost', args.notify_port, NotifyAPI(backends=args.backends)).serve_forever()

multiprocessing.Process(target=run_rest).start()
multiprocessing.Process(target=run_notify).start()
