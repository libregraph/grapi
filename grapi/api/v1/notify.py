# SPDX-License-Identifier: AGPL-3.0-or-later
from .api import API, APIResource
from .config import PREFIX


class NotifyAPI(API):
    def __init__(self, options=None, middleware=None, backends=None):
        if backends is None:
            backends = ['kopano']

        supported_backends = ['kopano']

        super().__init__(media_type=None, middleware=middleware)

        for backend in backends:
            if backend in supported_backends:  # TODO multiple would require prefix selection
                self.add_routes(backend, options)

    def add_routes(self, backend_name, options):
        backend = self.import_backend(backend_name, options)
        subscriptions = APIResource(backend.SubscriptionResource(options))

        self.add_route(PREFIX+'/subscriptions', subscriptions)
        self.add_route(PREFIX+'/subscriptions/{subscriptionid}', subscriptions)
