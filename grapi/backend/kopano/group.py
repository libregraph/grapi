# SPDX-License-Identifier: AGPL-3.0-or-later
import kopano

from . import user  # import as module since this is a circular import
from .resource import DEFAULT_TOP, Resource
from .utils import HTTPBadRequest, _get_group_by_id, experimental


@experimental
class GroupResource(Resource):
    fields = {
        'id': lambda group: group.groupid,
        'displayName': lambda group: group.name,
        'mail': lambda group: group.email,
    }

    def handle_get_members(self, req, resp, server, groupid):
        group = _get_group_by_id(server, groupid)
        data = (group.users(), DEFAULT_TOP, 0, 0)
        self.respond(req, resp, data, user.UserResource.fields)

    def handle_get(self, req, resp, server, groupid):
        if groupid:
            if groupid == 'delta':
                self._handle_get_delta(req, resp, server=server)
            else:
                self._handle_get_with_groupid(req, resp, server=server, groupid=groupid)
        else:
            self._handle_get_without_groupid(req, resp, server=server)

    def _handle_get_delta(self, req, resp, server):
        req.context.deltaid = '{groupid}'
        self.delta(req, resp, server)

    def _handle_get_with_groupid(self, req, resp, server, groupid):
        data = _get_group_by_id(server, groupid)
        self.respond(req, resp, data)

    def _handle_get_without_groupid(self, req, resp, server):
        data = (server.groups(), DEFAULT_TOP, 0, 0)
        self.respond(req, resp, data)

    @experimental
    def on_get_member_of(self, req, resp):
        server, _, userid = req.context.server_store

        if not userid and req.path.split('/')[-1] != 'users':
            userid = kopano.Store(server=server, mapiobj=server.mapistore).user.userid

        user = server.user(userid=userid)
        data = (user.groups(), DEFAULT_TOP, 0, 0)
        self.respond(req, resp, data, self.fields)

    def on_get_members(self, req, resp, groupid):
        """Return members by group ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            groupid (str): group ID.
        """
        server = req.context.server_store[0]
        self.handle_get_members(req, resp, server, groupid)

    def on_get(self, req, resp, userid=None, groupid=None, method=None):
        handler = None

        if method == 'members':
            handler = self.handle_get_members

        elif method:
            raise HTTPBadRequest("Unsupported group segment '%s'" % method)

        else:
            handler = self.handle_get

        server, store, userid = req.context.server_store
        handler(req, resp, server=server, groupid=groupid)
