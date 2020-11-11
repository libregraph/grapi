# SPDX-License-Identifier: AGPL-3.0-or-later
import importlib

from .decorators import requireResourceHandler, resourceException

try:  # falcon 2.0+
    from falcon import APP as FalconAPI
except ImportError:  # falcon 1.0
    from falcon import API as FalconAPI



class API(FalconAPI):
    def import_backend(self, name, options):
        backend = importlib.import_module('grapi.backend.%s' % name)
        if hasattr(backend, 'initialize'):
            backend.initialize(options)
        return backend


class APIResource:
    def __init__(self, resource):
        self._resource = resource

    def getResource(self, req):
        return self._resource

    def exceptionHandler(self, ex, req, resp, **params):
        resource = self.getResource(req)
        if resource and hasattr(resource, 'exceptionHandler'):
            resource.exceptionHandler(ex, req, resp, **params)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_get(self, req, resp, *args, **kwargs):
        return self.getResource(req).on_get(req, resp, *args, **kwargs)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_post(self, req, resp, *args, **kwargs):
        return self.getResource(req).on_post(req, resp, *args, **kwargs)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_patch(self, req, resp, *args, **kwargs):
        return self.getResource(req).on_patch(req, resp, *args, **kwargs)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_put(self, req, resp, *args, **kwargs):
        return self.getResource(req).on_put(req, resp, *args, **kwargs)

    @resourceException(handler=exceptionHandler)
    @requireResourceHandler
    def on_delete(self, req, resp, *args, **kwargs):
        return self.getResource(req).on_delete(req, resp, *args, **kwargs)
