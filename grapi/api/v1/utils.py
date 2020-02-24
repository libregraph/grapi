# SPDX-License-Identifier: AGPL-3.0-or-later


def _header_args(req, name):  # TODO use urlparse.parse_qs or similar..?
    d = {}
    header = req.get_header(name)
    if header:
        for arg in header.split(';'):
            k, v = arg.split('=')
            d[k] = v
    return d


def _header_sub_arg(req, name, arg):
    args = _header_args(req, name)
    if arg in args:
        return args[arg].strip('"')
