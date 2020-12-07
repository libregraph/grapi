# SPDX-License-Identifier: AGPL-3.0-or-later
import logging

import falcon

from grapi.api.common import API
from MAPI.Struct import MAPIErrorInvalidEntryid

from .api import APIResource
from .batch import BatchResource
from .config import PREFIX
from .healthcheck import HealthCheckResource
from .prefer import Prefer
from .request import Request
from .timezone import to_timezone
from .utils import suffix_method_caller


class BackendMiddleware:
    def __init__(self, name_backend, default_backend, options):
        self.name_backend = name_backend
        self.default_backend = default_backend
        self.options = options

    def process_resource(self, req, resp, resource, params):
        if not isinstance(resource, BackendResource):
            return

        prefer = req.context.prefer = Prefer(req)

        # Common request validaton.
        prefer_timeZone = prefer.get('outlook.timezone', raw=True)
        if prefer_timeZone:
            try:
                prefer_tzinfo = to_timezone(prefer_timeZone)
            except Exception:
                logging.debug('unsupported timezone value received in request: %s', prefer_timeZone)
                raise falcon.HTTPBadRequest(description="Provided prefer timezone value is not supported.")
            prefer.update('outlook.timezone', (prefer_tzinfo, prefer_timeZone))

        # Backend selection.

        backend = None

        # userid prefixed with backend name, e.g. imap.userid
        userid = params.get('userid')
        if userid:
            # TODO handle unknown backend
            for name in self.name_backend:
                if userid.startswith(name+'.'):
                    backend = self.name_backend[name]
                    params['userid'] = userid[len(name)+1:]
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


class BackendResource(APIResource):
    def __init__(self, default_backend, resource_name):
        super().__init__(resource=None)

        self.default_backend = default_backend
        self.name = resource_name

    def getResource(self, req):
        # Resource is per request, injected by BackendMiddleware.
        return req.context.resource


class RestAPI(API):
    def __init__(self, options=None, middleware=None, backends=None):
        if backends is None:
            backends = ['kopano']

        name_backend = {}
        for name in backends:
            backend = self.import_backend(name, options)
            name_backend[name] = backend

        # TODO(jelle): make backends define their types by introducting a constant in grapi.api
        # And specifying it in backends.
        backend_types = {
            'ldap': ['directory'],
            'kopano': ['directory', 'mail', 'calendar', 'reminder'],
            'imap': ['mail'],
            'caldav': ['calendar'],
            'mock': ['mail', 'directory'],
        }

        default_backend = {}
        for type_ in ('directory', 'mail', 'calendar', 'reminder'):
            for name, types in backend_types.items():
                if name in backends and type_ in types:
                    default_backend[type_] = name_backend[name]  # TODO type occurs twice

        middleware = (middleware or []) + [BackendMiddleware(name_backend, default_backend, options)]
        super().__init__(media_type=None, request_type=Request, middleware=middleware)

        self.req_options.strip_url_path_trailing_slash = True

        self.set_suffix_method_caller(suffix_method_caller)
        self.add_routes(default_backend, options)

    def route(self, path, resource, method=True):
        self.add_route(path, resource)
        if method:  # TODO make optional in a better way?
            self.add_route(path+'/{method}', resource)

    def add_routes(self, default_backend, options):
        healthCheck = HealthCheckResource()
        self.add_route('/health-check', healthCheck)

        batchEndpoint = BatchResource(None, self)
        self.add_route(PREFIX + '/$batch', batchEndpoint)

        directory = default_backend.get('directory')
        if directory:
            users = BackendResource(directory, 'UserResource')
            groups = BackendResource(directory, 'GroupResource')
            contactfolders = BackendResource(directory, 'ContactFolderResource')
            contacts = BackendResource(directory, 'ContactResource')
            photos = BackendResource(directory, 'ProfilePhotoResource')

            self.add_route(PREFIX + '/me', users)
            self.add_route(PREFIX + '/users', users)
            self.add_route(PREFIX + '/users/{userid}', users)

            self.add_route(PREFIX + '/groups', groups)
            self.add_route(PREFIX + '/groups/{groupid}', groups)

            for user in (PREFIX + '/me', PREFIX + '/users/{userid}'):
                self.add_route(user + '/contactFolders/', contactfolders, suffix="contact_folders")
                self.add_route(user + '/contactFolders/{folderid}', contactfolders)
                self.add_route(user + '/contacts/', contacts, suffix="contacts")
                self.add_route(user + '/contacts/{itemid}', contacts)
                self.add_route(user + '/contactFolders/{folderid}/contacts/{itemid}', contacts)

                self.add_route(user + '/photo', photos)
                self.add_route(user + '/photos/', photos, suffix="photos")
                self.add_route(user + '/photos/{photoid}', photos)

                self.add_route(user + '/contacts/{itemid}/photo', photos)
                self.add_route(user + '/contacts/{itemid}/photos/{photoid}', photos)
                self.add_route(user + '/contactFolders/{folderid}/contacts/{itemid}/photo', photos)
                self.add_route(user + '/contactFolders/{folderid}/contacts/{itemid}/photos/{photoid}', photos)

                self.add_route(user + '/memberOf', groups, suffix="member_of")

        mail = default_backend.get('mail')
        if mail:
            messages = BackendResource(mail, 'MessageResource')
            attachments = BackendResource(mail, 'AttachmentResource')
            mailfolders = BackendResource(mail, 'MailFolderResource')

            for user in (PREFIX + '/me', PREFIX + '/users/{userid}'):
                self.add_route(user + '/mailFolders', mailfolders, suffix="mail_folders")
                self.add_route(user + '/mailFolders/{folderid}', mailfolders)
                self.add_route(user + '/mailFolders/{folderid}/childFolders', mailfolders, suffix="child_folders")

                self.add_route(user + '/mailFolders/{folderid}/copy', mailfolders, suffix="copy_folder")
                self.add_route(user + '/mailFolders/{folderid}/move', mailfolders, suffix="move_folder")

                self.add_route(user + '/messages', messages, suffix="messages")
                self.add_route(user + '/messages/{itemid}', messages, suffix="message_by_itemid")
                self.add_route(user + '/mailFolders/{folderid}/messages', messages, suffix="messages_by_folderid")
                self.add_route(user + '/mailFolders/{folderid}/messages/{itemid}', messages)

                # Message attachments
                self.add_route(user + '/messages/{itemid}/attachments',
                               attachments, suffix="by_id")
                self.add_route(user + '/messages/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="by_id")
                self.add_route(user + '/messages/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_by_id")
                self.add_route(user + '/mailFolders/{folderid}/messages/{itemid}/attachments',
                               attachments, suffix="in_folder_by_id")
                self.add_route(user + '/mailFolders/{folderid}/messages/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="in_folder_by_id")
                self.add_route(user + '/mailFolders/{folderid}/messages/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_in_folder_by_id")

        calendar = default_backend.get('calendar')
        reminder = default_backend.get('reminder')
        if calendar:
            calendars = BackendResource(calendar, 'CalendarResource')
            reminders = BackendResource(reminder, 'ReminderResource')
            events = BackendResource(calendar, 'EventResource')
            attachments = BackendResource(calendar, 'AttachmentResource')

            for user in (PREFIX + '/me', PREFIX + '/users/{userid}'):
                self.add_route(user + '/calendar', calendars, suffix="calendar")
                self.add_route(user + '/calendars', calendars, suffix="calendars")
                self.add_route(user + '/calendars/{folderid}', calendars)

                self.add_route(user + '/events', events, suffix="events")
                self.add_route(user + '/events/{eventid}', events, suffix="by_eventid")
                self.add_route(user + '/events/{eventid}/accept', events, suffix="accept_event")
                self.add_route(user + '/events/{eventid}/decline', events, suffix="decline_event")
                self.add_route(user + '/events/{eventid}/instances', events, suffix="instances")

                self.add_route(user + '/calendar/events/{eventid}', events, suffix="by_eventid")
                self.add_route(user + '/calendar/events/{eventid}/accept', events, suffix="accept_event")

                self.add_route(user + '/calendars/{folderid}/events', events, suffix="by_folderid")
                self.add_route(user + '/calendars/{folderid}/events/{eventid}/accept', events,
                               suffix="accept_event_by_folderid")
                self.add_route(user + '/calendars/{folderid}/events/{eventid}/decline', events,
                               suffix="decline_event_by_folderid")
                self.add_route(user + '/calendars/{folderid}/events/{eventid}/instances', events,
                               suffix="instances_by_folderid")
                self.add_route(user + '/calendars/{folderid}/events/{eventid}', events, suffix="by_folderid_eventid")

                # Event attachments
                self.add_route(user + '/events/{itemid}/attachments',
                               attachments, suffix="by_id")
                self.add_route(user + '/events/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="by_id")
                self.add_route(user + '/events/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_by_id")
                self.add_route(user + '/calendar/events/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="by_id")
                self.add_route(user + '/calendar/events/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_by_id")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}/attachments',
                               attachments, suffix="in_folder_by_id")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}/attachments/{attachmentid}',
                               attachments, suffix="in_folder_by_id")
                self.add_route(user + '/calendars/{folderid}/events/{itemid}/attachments/{attachmentid}/$value',
                               attachments, suffix="binary_in_folder_by_id")

                self.add_route(user + '/calendars/{folderid}/calendarView', calendars,
                               suffix="calendar_view_by_folderid")
                self.add_route(user + '/calendarView', calendars, suffix="calendar_view")
                self.add_route(user + '/reminderView', reminders, suffix="reminder_view")
