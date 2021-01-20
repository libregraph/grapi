#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import sys

import kopano

kopano.set_bin_encoding('base64')


KOPANO_SOCKET = 'file:///var/run/kopano/server.sock'


def main(userid, socket, ssl_keyfile, ssl_pass):
    try:
        server = kopano.server(server_socket=socket, sslkey_file=ssl_keyfile, sslkey_pass=ssl_pass, parse_args=False)
    except Exception as excinfo:
        print("Unable to connect to '{}', '{}'".format(socket, excinfo))
        sys.exit(-1)

    try:
        user = server.user(userid=userid)
    except kopano.errors.NotFoundError:
        print('user not found on this server', file=sys.stderr)
        sys.exit(-1)

    kopano.set_bin_encoding('hex')

    print('Username: {}'.format(user.name))
    print('Fullname: {}'.format(user.fullname))
    if user.store:
        print('Store: {}'.format(user.store.guid))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='resolve userid to kopano User')
    parser.add_argument('--userid', type=str, help='the userid to resolve', required=True)
    parser.add_argument('--socket', type=str, default=KOPANO_SOCKET,
                        help='the kopano server socket (default: {})'.format(KOPANO_SOCKET))
    parser.add_argument('--ssl-keyfile', type=str, help='the kopano SSL key file')
    parser.add_argument('--ssl-pass', type=str, default='', help='the kopano SSL key file')

    args = parser.parse_args()
    main(args.userid, args.socket, args.ssl_keyfile, args.ssl_pass)
