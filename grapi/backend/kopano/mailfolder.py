# SPDX-License-Identifier: AGPL-3.0-or-later

import falcon
import kopano
from MAPI.Struct import MAPIErrorCollision

from grapi.api.v1.resource import HTTPBadRequest, HTTPConflict

from .folder import FolderResource
from .message import MessageResource
from .schema import destination_id_schema, folder_schema
from .utils import _folder, experimental


class DeletedMailFolderResource(FolderResource):
    fields = {
        '@odata.type': lambda folder: '#microsoft.graph.mailFolder',  # TODO
        'id': lambda folder: folder.entryid,
        '@removed': lambda folder: {'reason': 'deleted'}  # TODO soft deletes
    }


@experimental
class MailFolderResource(FolderResource):
    fields = FolderResource.fields.copy()
    fields.update({
        'parentFolderId': lambda folder: folder.parent.entryid,
        'displayName': lambda folder: folder.name,
        'unreadItemCount': lambda folder: folder.unread,
        'totalItemCount': lambda folder: folder.count,
        'childFolderCount': lambda folder: folder.subfolder_count,
    })

    relations = {
        'childFolders': lambda folder: (folder.folders, MailFolderResource),
        'messages': lambda folder: (folder.items, MessageResource)  # TODO event msgs
    }

    # field map for $orderby query
    sorting_field_map = {
        "subject": "subject",
        "receivedDateTime": "received",
        "createdDateTime": "created",
    }

    deleted_resource = DeletedMailFolderResource
    container_classes = (None, 'IPF.Note')

    def on_get_child_folders(self, req, resp, folderid):
        _, store, _ = req.context.server_store
        data = _folder(store, folderid)
        data = self.generator(req, data.folders, data.subfolder_count_recursive)
        self.respond(req, resp, data)

    def folder_gen(self, req, folder):
        args = self.parse_qs(req)
        if '$orderby' in args:
            for index, field in enumerate(args['$orderby']):
                if field.startswith("-") or field.startswith("+"):
                    field_order = field[0]
                    field = field[1:]
                else:
                    field_order = ''
                if field in self.sorting_field_map:
                    args['$orderby'][index] = field_order + self.sorting_field_map[field]
                else:
                    # undefined fields have to be removed.
                    del args['$orderby'][index]

        if '$search' in args:
            query = args['$search'][0]

            def yielder(**kwargs):
                for item in folder.items(query=query):
                    yield item
            return self.generator(req, yielder, 0, args=args)
        else:
            return self.generator(req, folder.items, folder.count, args=args)

    def handle_get(self, req, resp, store, folderid):
        if folderid:
            if folderid == 'delta':
                self._handle_get_delta(req, resp, store=store)
            else:
                self._handle_get_with_folderid(req, resp, store=store, folderid=folderid)

    def _handle_get_delta(self, req, resp, store):
        req.context.deltaid = '{folderid}'
        self.delta(req, resp, store=store)

    def _handle_get_with_folderid(self, req, resp, store, folderid):
        data = _folder(store, folderid)
        if not data:
            raise falcon.HTTPNotFound(description="folder not found")
        self.respond(req, resp, data)

    @experimental
    def on_get_mail_folders(self, req, resp, userid=None):
        """Handle GET request on mailFolders.

        Args:
            userid (Optional[str): user ID.
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        store = req.context.server_store[1]
        data = self.generator(req, store.mail_folders, 0)
        self.respond(req, resp, data, MailFolderResource.fields)

    def on_get(self, req, resp, userid=None, folderid=None, method=None):
        if method is None:
            handler = self.handle_get
        else:
            raise HTTPBadRequest("Unsupported mailFolder segment '%s'" % method)

        server, store, userid = req.context.server_store
        handler(req, resp, store=store, folderid=folderid)

    def on_post_child_folders(self, req, resp, folderid):
        fields = self.load_json(req)
        self.validate_json(folder_schema, fields)

        store = req.context.server_store[1]

        folder = _folder(store, folderid)
        if folder.get_folder(fields['displayName']):
            raise HTTPConflict("'%s' already exists" % fields['displayName'])
        child = folder.create_folder(fields['displayName'])
        resp.status = falcon.HTTP_201
        self.respond(req, resp, child, MailFolderResource.fields)

    def on_post_copy_folder(self, req, resp, folderid):
        _, store, _ = req.context.server_store
        self._handle_post_copyOrMove(req, resp, store=store, folderid=folderid, move=False)

    def on_post_move_folder(self, req, resp, folderid):
        _, store, _ = req.context.server_store
        self._handle_post_copyOrMove(req, resp, store=store, folderid=folderid, move=True)

    def _handle_post_copyOrMove(self, req, resp, store, folderid, move=False):
        """Handle POST request for Copy or Move actions."""
        fields = self.load_json(req)
        self.validate_json(destination_id_schema, fields)
        folder = _folder(store, folderid)
        if not folder:
            raise falcon.HTTPNotFound(description="source folder not found")

        to_folder = store.folder(entryid=fields['destinationId'].encode('ascii'))  # TODO ascii?
        if not to_folder:
            raise falcon.HTTPNotFound(description="destination folder not found")

        if not move:
            try:
                folder.parent.copy(folder, to_folder)
            except MAPIErrorCollision:
                raise HTTPConflict("copy has failed because some items already exists")
        else:
            try:
                folder.parent.move(folder, to_folder)
            except MAPIErrorCollision:
                raise HTTPConflict("move has failed because some items already exists")

        new_folder = to_folder.folder(folder.name)
        self.respond(req, resp, new_folder, MailFolderResource.fields)

    @experimental
    def on_post_mail_folders(self, req, resp):
        _, store, _ = req.context.server_store
        fields = self.load_json(req)
        self.validate_json(folder_schema, fields)
        try:
            folder = store.create_folder(fields['displayName'])
        except kopano.errors.DuplicateError:
            raise HTTPConflict("'%s' folder already exists" % fields['displayName'])
        resp.status = falcon.HTTP_201
        self.respond(req, resp, folder, MailFolderResource.fields)

    def on_post(self, req, resp, userid=None, folderid=None):
        raise HTTPBadRequest("Unsupported in mailfolder")
