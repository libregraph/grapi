# SPDX-License-Identifier: AGPL-3.0-or-later
import codecs
import logging

import falcon
import kopano

from grapi.api.v1.schema import user as user_schema

from . import group  # import as module since this is a circular import
from .contact import ContactResource
from .message import MessageResource
from .resource import DEFAULT_TOP, Resource
from .utils import HTTPBadRequest, HTTPNotFound, experimental


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
        'businessPhones': lambda user: getattr(user, "business_phones", []),
    }

    complementary_fields = {
        'companyName': lambda user: user.company.name,
        'postalCode': lambda user: getattr(user, "postal_code", ""),
    }

    individual_fields = {
        'preferredName': lambda user: getattr(user, "preferred_name", ""),
        'birthday': lambda user: getattr(user, "birthday", ""),
    }

    # GET

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
                self._handle_get_delta(req, resp, server=server)
            else:
                self._handle_get_with_userid(req, resp, server=server, userid=userid)
        else:
            self._handle_get_without_userid(req, resp, server=server)

    @experimental
    def _handle_get_delta(self, req, resp, server):
        req.context.deltaid = '{userid}'
        self.delta(req, resp, server=server)

    def _handle_get_with_userid(self, req, resp, server, userid):
        data = server.user(userid=userid)
        self.respond(req, resp, data)

    def _handle_get_without_userid(self, req, resp, server):
        args = self.parse_qs(req)
        userid = kopano.Store(server=server, mapiobj=server.mapistore).user.userid
        try:
            company = server.user(userid=userid).company
        except kopano.errors.NotFoundError:
            logging.warning('failed to get company for user %s', userid, exc_info=True)
            raise HTTPNotFound(description="The company wasn't found")
        query = None
        if '$search' in args:
            query = args['$search'][0]

        def yielder(**kwargs):
            yield from company.users(hidden=False, inactive=False, query=query, **kwargs)
        data = self.generator(req, yielder)
        self.respond(req, resp, data)

    @experimental
    def handle_get_contacts(self, req, resp, store, server, userid):
        data = self.folder_gen(req, store.contacts)
        self.respond(req, resp, data, ContactResource.fields)

    @experimental
    def handle_get_memberOf(self, req, resp, store, server, userid):
        user = server.user(userid=userid)
        data = (user.groups(), DEFAULT_TOP, 0, 0)
        self.respond(req, resp, data, group.GroupResource.fields)

    def on_get_me(self, req, resp):
        """Return 'me' user info.

        :param req: Falcon request object.
        :type req: Request
        :param resp: Falcon response object.
        :type resp: Response
        """
        server, _, userid = req.context.server_store
        userid = kopano.Store(server=server, mapiobj=server.mapistore).user.userid
        self._handle_get_with_userid(req, resp, server, userid)

    def on_get_users(self, req, resp):
        """Return list of all users.

        :param req: Falcon request object.
        :type req: Request
        :param resp: Falcon response object.
        :type resp: Response
        """
        server = req.context.server_store[0]
        self._handle_get_without_userid(req, resp, server=server)

    def on_get_by_userid(self, req, resp, userid):
        """Return a user info by ID.

        :param req: Falcon request object.
        :type req: Request
        :param resp: Falcon response object.
        :type resp: Response
        :param userid: user ID.
        :type userid: str
        """
        server = req.context.server_store[0]
        self._handle_get_with_userid(req, resp, server, userid)

    # TODO redirect to other resources?
    def on_get(self, req, resp, userid=None, method=None):
        handler = None

        if not method:
            handler = self.handle_get

        elif method == 'contacts':
            handler = self.handle_get_contacts

        elif method == 'memberOf':
            handler = self.handle_get_memberOf

        elif method:
            raise HTTPBadRequest("Unsupported user segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in user")

        server, store, userid = req.context.server_store
        if not userid and req.path.split('/')[-1] != 'users':
            userid = kopano.Store(server=server, mapiobj=server.mapistore).user.userid
        handler(req, resp, store=store, server=server, userid=userid)

    # POST

    @experimental
    def on_post_sendMail(self, req, resp):
        store = req.context.server_store[1]
        fields = req.context.json_data
        self.validate_json(user_schema.sendmail_schema_validator, fields)

        message = self.create_message(store.outbox, fields['message'], MessageResource.set_fields)
        copy_to_sentmail = fields.get('SaveToSentItems', 'true') == 'true'
        message.send(copy_to_sentmail=copy_to_sentmail)
        resp.status = falcon.HTTP_202

    @experimental
    def handle_post_contacts(self, req, resp, fields, store):
        item = self.create_message(store.contacts, fields, ContactResource.set_fields)
        self.respond(req, resp, item, ContactResource.fields)

    # TODO redirect to other resources?
    def on_post(self, req, resp, userid=None, method=None):
        handler = None

        if method:
            raise HTTPBadRequest("Unsupported user segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in user")

        server, store, userid = req.context.server_store
        fields = req.context.json_data
        handler(req, resp, fields=fields, store=store)
