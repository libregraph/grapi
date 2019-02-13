# SPDX-License-Identifier: AGPL-3.0-or-later
from .config import PREFIX

import falcon

class BackendResource(object): # TODO merge with rest.py
    def __init__(self, resource):
        self.resource = resource

    def on_get(self, *args, **kwargs):
        return self.resource.on_get(*args, **kwargs)

    def on_post(self, *args, **kwargs):
        return self.resource.on_post(*args, **kwargs)

    def on_patch(self, *args, **kwargs):
        return self.resource.on_patch(*args, **kwargs)

    def on_put(self, *args, **kwargs):
        return self.resource.on_put(*args, **kwargs)

    def on_delete(self, *args, **kwargs):
        return self.resource.on_delete(*args, **kwargs)

class NotifyAPI(falcon.API):
    def __init__(self, options=None, middleware=None, backends=None):
#        backends = ['ldap', 'imap', 'caldav']

        if backends is None:
            backends = ['kopano']

        supported_backends = ['kopano']

        self.options = options
        super().__init__(media_type=None, middleware=middleware)

        for backend in backends:
            if backend in supported_backends: # TODO multiple would require prefix selection
                self.add_routes(backend, options)

    def import_backend(self, name): # TODO share with rest.py
        # import ..backend.<name>
        return __import__('backend.'+name, globals=globals(), fromlist=[''], level=2)

    def add_routes(self, backend_name, options):
        backend = self.import_backend(backend_name)
        subscriptions = backend.SubscriptionResource(options)

        self.add_route(PREFIX+'/subscriptions', subscriptions)
        self.add_route(PREFIX+'/subscriptions/{subscriptionid}', subscriptions)
