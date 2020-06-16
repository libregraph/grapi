#!/usr/bin/python3
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# /$batch endpoint json body generator, usage:
# hey -c 1  -m POST -H "Authorization: Bearer $TOKEN_VALUE" -H "Content-Type: application/json" -D ~/projects/grapi/batch.json   "https://starfighter.kopano.lan:8097/api/gc/v1/\$batch"


import argparse
import json
import sys

import kopano

kopano.set_bin_encoding('base64')


KOPANO_SOCKET = 'file:///var/run/kopano/server.sock'
USER_LIMIT = 25


def main(jsonfile, limit, socket, ssl_keyfile, ssl_pass):
    try:
        server = kopano.Server(server_socket=socket, sslkey_file=ssl_keyfile, sslkey_pass=ssl_pass, parse_args=False)
    except Exception as excinfo:
        print("Unable to connect to '{}', '{}'".format(socket, excinfo))
        sys.exit(-1)

    requests = []
    limit += 1

    for index, user in enumerate(server.users()):
        index += 1  # graph's index starts at 1

        if index == limit:
            break

        request = {
            'id': index,
            'method': 'GET',
            'url': '/api/gc/v1/users/{}'.format(user.userid)
        }

        requests.append(request)

    data = {}
    data['requests'] = requests
    with open(jsonfile, 'w') as fp:
        fp.write(json.dumps(data, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create json body for posting to the /$batch endpoint')
    parser.add_argument('--output-file', type=str, help='the file to write the json body to',
                        required=True)
    parser.add_argument('--total', type=int, help='the amount of users endpoint requests (default: {})'.format(USER_LIMIT),
                        default=USER_LIMIT)
    parser.add_argument('--socket', type=str, default=KOPANO_SOCKET,
                        help='the kopano server socket (default: {})'.format(KOPANO_SOCKET))
    parser.add_argument('--ssl-keyfile', type=str, help='the kopano SSL key file')
    parser.add_argument('--ssl-pass', type=str, default='', help='the kopano SSL key file')

    args = parser.parse_args()
    main(args.output_file, args.total, args.socket, args.ssl_keyfile, args.ssl_pass)
