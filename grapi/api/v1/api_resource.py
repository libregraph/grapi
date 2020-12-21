# SPDX-License-Identifier: AGPL-3.0-or-later
from .decorators import requireResourceHandler, resourceException


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


class BackendResource(APIResource):
    def __init__(self, default_backend, resource_name):
        super().__init__(resource=None)

        self.default_backend = default_backend
        self.name = resource_name

    @staticmethod
    def getResource(req):
        # Resource is per request, injected by BackendMiddleware.
        return req.context.resource
