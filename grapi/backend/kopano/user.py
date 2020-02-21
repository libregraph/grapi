# SPDX-License-Identifier: AGPL-3.0-or-later
import codecs
import falcon
import logging

import kopano  # TODO remove?

from .utils import (
    _server_store, HTTPBadRequest, HTTPNotFound, experimental
)
from .resource import (
    DEFAULT_TOP, Resource, _start_end
)
from .calendar import CalendarResource
from .contact import ContactResource
from .contactfolder import ContactFolderResource
from .event import EventResource
from .mailfolder import MailFolderResource
from .message import MessageResource
from .reminder import ReminderResource
from .schema import event_schema
from . import group  # import as module since this is a circular import
from .profilephoto import (
    ProfilePhotoResource
)


class UserImporter:
    def __init__(self):
        self.updates = []
        self.deletes = []

    def update(self, user):
        self.updates.append(user)

    def delete(self, user):
        self.deletes.append(user)


class DeletedUserResource(Resource):
    fields = {
        'id': lambda user: user.userid,
        #       '@odata.type': lambda item: '#microsoft.graph.message', # TODO
        '@removed': lambda item: {'reason': 'deleted'}  # TODO soft deletes
    }


class UserResource(Resource):
    fields = {
        'id': lambda user: user.userid,
        'displayName': lambda user: user.fullname,
        'jobTitle': lambda user: user.job_title,
        'givenName': lambda user: user.first_name,
        'mail': lambda user: user.email,
        'mobilePhone': lambda user: user.mobile_phone,
        'officeLocation': lambda user: user.office_location,
        'surname': lambda user: user.last_name,
        'userPrincipalName': lambda user: user.name,
    }

    def delta(self, req, resp, server):
        args = self.parse_qs(req)
        token = args['$deltatoken'][0] if '$deltatoken' in args else None
        importer = UserImporter()
        newstate = server.sync_gab(importer, token)
        changes = [(o, UserResource) for o in importer.updates] + \
            [(o, DeletedUserResource) for o in importer.deletes]
        data = (changes, DEFAULT_TOP, 0, len(changes))
        deltalink = b"%s?$deltatoken=%s" % (req.path.encode('utf-8'), codecs.encode(newstate, 'ascii'))
        self.respond(req, resp, data, UserResource.fields, deltalink=deltalink)

    def handle_get(self, req, resp, store, server, userid):
        if userid:
            if userid == 'delta':
                self._handle_get_delta(req, resp, store=store, server=server)
            else:
                self._handle_get_with_userid(req, resp, store=store, server=server, userid=userid)
        else:
            self._handle_get_without_userid(req, resp, store=store, server=server)

    @experimental
    def _handle_get_delta(self, req, resp, store, server):
        req.context.deltaid = '{userid}'
        self.delta(req, resp, server=server)

    def _handle_get_with_userid(self, req, resp, store, server, userid):
        data = server.user(userid=userid)
        self.respond(req, resp, data)

    def _handle_get_without_userid(self, req, resp, store, server):
        args = self.parse_qs(req)
        userid = kopano.Store(server=server, mapiobj=server.mapistore).user.userid
        try:
            company = server.user(userid=userid).company
        except kopano.errors.NotFoundError:
            logging.warn('failed to get company for user %s', userid, exc_info=True)
            raise HTTPNotFound(description="The company wasn't found")
        query = None
        if '$search' in args:
            query = args['$search'][0]

        def yielder(**kwargs):
            yield from company.users(hidden=False, inactive=False, query=query, **kwargs)
        data = self.generator(req, yielder)
        self.respond(req, resp, data)

    @experimental
    def handle_get_mailFolders(self, req, resp, store, server, userid):
        data = self.generator(req, store.mail_folders, 0)
        self.respond(req, resp, data, MailFolderResource.fields)

    @experimental
    def handle_get_contactFolders(self, req, resp, store, server, userid):
        data = self.generator(req, store.contact_folders, 0)
        self.respond(req, resp, data, ContactFolderResource.fields)

    @experimental
    def handle_get_messages(self, req, resp, store, server, userid):
        data = self.folder_gen(req, store.inbox)
        self.respond(req, resp, data, MessageResource.fields)

    @experimental
    def handle_get_contacts(self, req, resp, store, server, userid):
        data = self.folder_gen(req, store.contacts)
        self.respond(req, resp, data, ContactResource.fields)

    @experimental
    def handle_get_calendars(self, req, resp, store, server, userid):
        data = self.generator(req, store.calendars, 0)
        self.respond(req, resp, data, CalendarResource.fields)

    @experimental
    def handle_get_events(self, req, resp, store, server, userid):
        calendar = store.calendar
        data = self.generator(req, calendar.items, calendar.count)
        self.respond(req, resp, data, EventResource.fields)

    @experimental
    def handle_get_calendarView(self, req, resp, store, server, userid):
        start, end = _start_end(req)

        def yielder(**kwargs):
            for occ in store.calendar.occurrences(start, end, **kwargs):
                yield occ
        data = self.generator(req, yielder)
        self.respond(req, resp, data, EventResource.fields)

    @experimental
    def handle_get_reminderView(self, req, resp, store, server, userid):
        start, end = _start_end(req)

        def yielder(**kwargs):
            for occ in store.calendar.occurrences(start, end):
                if occ.reminder:
                    yield occ
        data = self.generator(req, yielder)
        self.respond(req, resp, data, ReminderResource.fields)

    @experimental
    def handle_get_memberOf(self, req, resp, store, server, userid):
        user = server.user(userid=userid)
        data = (user.groups(), DEFAULT_TOP, 0, 0)
        self.respond(req, resp, data, group.GroupResource.fields)

    @experimental
    def handle_get_photos(self, req, resp, store, server, userid):
        user = server.user(userid=userid)

        def yielder(**kwargs):
            photo = user.photo
            if photo:
                yield photo
        data = self.generator(req, yielder)
        self.respond(req, resp, data, ProfilePhotoResource.fields)

    # TODO redirect to other resources?
    def on_get(self, req, resp, userid=None, method=None):
        handler = None

        if not method:
            handler = self.handle_get

        elif method == 'mailFolders':
            handler = self.handle_get_mailFolders

        elif method == 'contactFolders':
            handler = self.handle_get_contactFolders

        elif method == 'messages':  # TODO store-wide?
            handler = self.handle_get_messages

        elif method == 'contacts':
            handler = self.handle_get_contacts

        elif method == 'calendars':
            handler = self.handle_get_calendars

        elif method == 'events':  # TODO multiple calendars?
            handler = self.handle_get_events

        elif method == 'calendarView':  # TODO multiple calendars? merge code with calendar.py
            handler = self.handle_get_calendarView

        elif method == 'reminderView':  # TODO multiple calendars?
            # TODO use restriction in pyko: calendar.reminders(start, end)?
            handler = self.handle_get_reminderView

        elif method == 'memberOf':
            handler = self.handle_get_memberOf

        elif method == 'photos':  # TODO multiple photos?
            handler = self.handle_get_photos

        elif method:
            raise HTTPBadRequest("Unsupported user segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in user")

        server, store, userid = _server_store(req, userid, self.options)
        if not userid and req.path.split('/')[-1] != 'users':
            userid = kopano.Store(server=server, mapiobj=server.mapistore).user.userid
        handler(req, resp, store=store, server=server, userid=userid)

    @experimental
    def handle_post_sendMail(self, req, resp, fields, store):
        message = self.create_message(store.outbox, fields['message'], MessageResource.set_fields)
        copy_to_sentmail = fields.get('SaveToSentItems', 'true') == 'true'
        message.send(copy_to_sentmail=copy_to_sentmail)
        resp.status = falcon.HTTP_202

    @experimental
    def handle_post_contacts(self, req, resp, fields, store):
        item = self.create_message(store.contacts, fields, ContactResource.set_fields)
        self.respond(req, resp, item, ContactResource.fields)

    @experimental
    def handle_post_messages(self, req, resp, fields, store):
        item = self.create_message(store.drafts, fields, MessageResource.set_fields)
        self.respond(req, resp, item, MessageResource.fields)

    @experimental
    def handle_post_events(self, req, resp, fields, store):
        self.validate_json(event_schema, fields)

        try:
            item = self.create_message(store.calendar, fields, EventResource.set_fields)
        except kopano.errors.ArgumentError as e:
            raise HTTPBadRequest("Invalid argument error '{}'".format(e))
        if fields.get('attendees', None):
            # NOTE(longsleep): Sending can fail with NO_ACCCESS if no permission to outbox.
            item.send()
        self.respond(req, resp, item, EventResource.fields)

    @experimental
    def handle_post_mailFolders(self, req, resp, fields, store):
        folder = store.create_folder(fields['displayName'])  # TODO exception on conflict
        self.respond(req, resp, folder, MailFolderResource.fields)

    # TODO redirect to other resources?
    def on_post(self, req, resp, userid=None, method=None):
        handler = None

        if method == 'sendMail':
            handler = self.handle_post_sendMail

        elif method == 'contacts':
            handler = self.handle_post_contacts

        elif method == 'messages':
            handler = self.handle_post_messages

        elif method == 'events':
            handler = self.handle_post_events

        elif method == 'mailFolders':
            handler = self.handle_post_mailFolders

        elif method:
            raise HTTPBadRequest("Unsupported user segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in user")

        server, store, userid = _server_store(req, userid, self.options)
        fields = self.load_json(req)
        handler(req, resp, fields=fields, store=store)
