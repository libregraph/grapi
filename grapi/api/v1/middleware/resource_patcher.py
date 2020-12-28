# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resource patcher middleware."""
import logging

import falcon
from MAPI.Struct import MAPIErrorInvalidEntryid

from grapi.api.common import API
from grapi.api.v1.api import BackendResource
from grapi.api.v1.prefer import Prefer
from grapi.api.v1.timezone import to_timezone


class ResourcePatcher:
    """Resource patcher to add related resource as a context."""

    def __init__(self, name_backend, default_backend, options):
        self.name_backend = name_backend
        self.default_backend = default_backend
        self.options = options

    def process_resource(self, req, resp, resource, params):
        """Built-in Falcon middleware method."""
        if not isinstance(resource, BackendResource):
            return

        prefer = req.context.prefer = Prefer(req)

        # Common request validaton.
        prefer_time_zone = prefer.get('outlook.timezone', raw=True)
        if prefer_time_zone:
            try:
                prefer_tzinfo = to_timezone(prefer_time_zone)
            except Exception:
                logging.debug('unsupported timezone value received in request: %s', prefer_time_zone)
                raise falcon.HTTPBadRequest(description="Provided prefer timezone value is not supported.")
            prefer.update('outlook.timezone', (prefer_tzinfo, prefer_time_zone))

        # Backend selection.

        backend = None

        # userid prefixed with backend name, e.g. imap.userid
        userid = params.get('userid')
        if userid:
            # TODO handle unknown backend
            for name in self.name_backend:
                if userid.startswith(name + '.'):
                    backend = self.name_backend[name]
                    params['userid'] = userid[len(name) + 1:]
                    break

        # fall back to default backend for type
        if not backend:
            backend = resource.default_backend

        resource_cls = getattr(backend, resource.name)

        # Add server store object for the user to the resource instance.
        if hasattr(resource_cls, "need_store") and resource_cls.need_store:
            backend_name = next(iter(self.name_backend))
            utils = API.import_backend("{}.utils".format(backend_name), None)
            userid = params.pop('userid') if 'userid' in params else None
            try:
                server, store, userid = utils._server_store(req, userid, self.options)
            except MAPIErrorInvalidEntryid:
                raise falcon.HTTPBadRequest("Invalid entryid provided")
            # User should have store.
            if not store:
                raise falcon.HTTPForbidden("No store found for the user")

            # Todo(mort), store User object in the Context instead of userid.
            req.context.server_store = server, store, userid

        # result: eg ldap.UserResource() or kopano.MessageResource()
        req.context.resource = resource_cls(self.options)
