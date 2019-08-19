# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon
import functools
import logging


def experimental(f, *args, **kwargs):
    def _experimental(req, resp, resource, params):
        if not resource.options.with_experimental:
            logging.debug('incoming request to disabled experimental endpoint: %s', req.path)
            raise falcon.HTTPNotFound()

    return falcon.before(_experimental, *args, **kwargs)(f)


def resourceException(_func=None, *, handler=None):
    def decoratorResourceException(f):
        @functools.wraps(f)
        def wrapperResourceException(resource, *args, **kwargs):
            try:
                return f(resource, *args, **kwargs)
            except Exception as e:
                if handler is not None:
                    handler(resource, e)
                raise
        return wrapperResourceException

    if _func is None:
        return decoratorResourceException
    else:
        return decoratorResourceException(_func)
