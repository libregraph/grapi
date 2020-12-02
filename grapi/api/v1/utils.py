# SPDX-License-Identifier: AGPL-3.0-or-later
from falcon import HTTPNotFound

from .resource import Resource


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


def suffix_method_caller(method_name, req, resp, **kwargs):
    """Call defined method inside a resource.

    Args:
        method_name (str): method name (e.g. on_get_me, on_get_users, ...).
        req (Request): Falcon request object.
        resp (Response): Falcon response object.

    Raises:
        HTTPNotFound
    """
    if isinstance(req.context.resource, Resource):
        if hasattr(req.context.resource, method_name):
            return getattr(req.context.resource, method_name)(req, resp, **kwargs)
    raise HTTPNotFound()
