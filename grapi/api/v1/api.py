# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon
import importlib

from .decorators import resourceException, requireResourceHandler


class API(falcon.API):
    def import_backend(self, name, options):
        backend = importlib.import_module('grapi.backend.%s' % name)
        if hasattr(backend, 'initialize'):
            backend.initialize(options)
        return backend


class APIResource:
    def __init__(self, resource):
        self.resource = resource

    def exceptionHandler(self, ex, req, resp, **params):
        if self.resource and hasattr(self.resource, 'exceptionHandler'):
            self.resource.exceptionHandler(ex, req, resp, **params)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_get(self, *args, **kwargs):
        return self.resource.on_get(*args, **kwargs)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_post(self, *args, **kwargs):
        return self.resource.on_post(*args, **kwargs)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_patch(self, *args, **kwargs):
        return self.resource.on_patch(*args, **kwargs)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_put(self, *args, **kwargs):
        return self.resource.on_put(*args, **kwargs)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_delete(self, *args, **kwargs):
        return self.resource.on_delete(*args, **kwargs)
