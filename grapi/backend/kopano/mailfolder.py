"""MailFolders resource implementation."""
# SPDX-License-Identifier: AGPL-3.0-or-later
from functools import partial

import falcon
import kopano
from kopano.query import _query_to_restriction
from MAPI.Struct import MAPIErrorCollision

from grapi.api.v1.resource import HTTPConflict, _parse_qs

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
    """MailFolder resource."""

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

    sorting_field_map = {
        "subject": "subject",
        "receivedDateTime": "received",
        "createdDateTime": "created",
    }

    deleted_resource = DeletedMailFolderResource

    # GET

    def _get_child_folder_by_id(self, req, folderid, childid):
        """Return childFolder by ID.

        Args:
            req (Request): Falcon request object.
            folderid (str): parent folder ID.
            childid (str): child folder ID.

        Returns:
            Tuple[Folder]: parent and child folder object.

        Raises:
            falcon.HTTPNotFound: when parent folder or child folder not found.
        """
        store = req.context.server_store[1]
        parent = _folder(store, folderid)
        if not parent:
            raise falcon.HTTPNotFound(description="folder not found")
        child = parent.get_folder(entryid=childid)
        if not child:
            raise falcon.HTTPNotFound(description="child folder not found")
        return parent, child

    @staticmethod
    def _gen_restriction(req, store):
        """Generate a restriction for folders based on request params.

        Args:
            req (Request): Falcon request object.
            store (Store): user's store object.

        Returns:
            Restriction: generated restriction object.
            None: when the request has no '$search' param.
        """
        args = _parse_qs(req)
        query = args["$search"] if '$search' in args else None
        if not query:
            return None

        return _query_to_restriction(query[0], "folder", store)

    def on_get_child_folders(self, req, resp, folderid):
        """Return childFolders list.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): parent folder ID.
        """
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        restriction = self._gen_restriction(req, store)
        if not restriction:
            fn = folder.folders
            count = folder.subfolder_count_recursive
        else:
            fn = partial(folder.folders, restriction=restriction)
            count = 0

        data = self.generator(req, fn, count)
        self.respond(req, resp, data)

    def on_get_mail_folder_by_id(self, req, resp, folderid):
        """Return info of a specific folder ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID.
        """
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        self.respond(req, resp, folder)

    def on_get_mail_folders_delta(self, req, resp):
        """Return mailFolder's delta info.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        store = req.context.server_store[1]
        req.context.deltaid = '{folderid}'
        self.delta(req, resp, store=store)

    @experimental
    def on_get_mail_folders(self, req, resp):
        """Return mailFolders list.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        store = req.context.server_store[1]
        restriction = self._gen_restriction(req, store)
        if not restriction:
            fn = store.mail_folders
        else:
            fn = partial(store.folders, recurse=False, restriction=restriction)
        data = self.generator(req, fn, 0)
        self.respond(req, resp, data, MailFolderResource.fields)

    def on_get_child_folder_by_id(self, req, resp, folderid, childid):
        """Get a childFolder by ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): parent folder ID.
            childid (str): child folder ID which should be removed.
        """
        child = self._get_child_folder_by_id(req, folderid, childid)[1]
        self.respond(req, resp, child, self.fields)

    # POST

    def on_post_child_folders(self, req, resp, folderid):
        """Create a new childFolder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): parent folder ID.

        Raises:
            HTTPConflict: when the folder already exists.
        """
        fields = self.load_json(req)
        self.validate_json(folder_schema, fields)

        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        try:
            child = folder.create_folder(fields['displayName'])
        except kopano.errors.DuplicateError as e:
            raise HTTPConflict(str(e))

        resp.status = falcon.HTTP_201
        self.respond(req, resp, child, self.fields)

    def on_post_copy_folder(self, req, resp, folderid):
        """Copy a folder to a destination.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): selected folder ID which need to be copied.
        """
        store = req.context.server_store[1]
        self._folder_copy_or_move(req, resp, store, folderid, move=False)

    def on_post_move_folder(self, req, resp, folderid):
        """Move a folder to a destination.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): selected folder ID which need to be moved.
        """
        store = req.context.server_store[1]
        self._folder_copy_or_move(req, resp, store, folderid, move=True)

    def _folder_copy_or_move(self, req, resp, store, folderid, move=False):
        """Copy or move a folder to a destination.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): selected folder ID which need to be copied or moved.
            move (bool): Is it 'move' or 'copy'?
                True means 'move' and False means 'copy' action.

        Raises:
            falcon.HTTPNotFound: when the origin or destination folder not found.
            falcon.HTTPConflict: when some items already exists in the destination.
        """
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
        self.respond(req, resp, new_folder, self.fields)

    @experimental
    def on_post_mail_folders(self, req, resp):
        """Create a new mailFolder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.

        Raises:
            HTTPConflict: when the folder already exists.
        """
        fields = self.load_json(req)
        self.validate_json(folder_schema, fields)

        store = req.context.server_store[1]
        try:
            folder = store.subtree.create_folder(
                fields['displayName'], container_class="IPF.Note"
            )
        except kopano.errors.DuplicateError as e:
            raise HTTPConflict(str(e))

        resp.status = falcon.HTTP_201
        self.respond(req, resp, folder, self.fields)

    # PATCH

    def on_patch_mail_folder_by_id(self, req, resp, folderid):
        """Update mailFolder by ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): target folder ID which should be updated.

        Raises:
            falcon.HTTPNotFound: when folder not found.
        """
        fields = self.load_json(req)
        self.validate_json(folder_schema, fields)

        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        if not folder:
            raise falcon.HTTPNotFound(description="folder not found")
        folder.name = fields["displayName"]

        self.respond(req, resp, folder, self.fields)

    def on_patch_child_folder_by_id(self, req, resp, folderid, childid):
        """Update mailFolder by ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): parent folder ID.
            childid (str): child folder ID which should be updated.
        """
        fields = self.load_json(req)
        self.validate_json(folder_schema, fields)

        child = self._get_child_folder_by_id(req, folderid, childid)[1]
        child.name = fields["displayName"]

        self.respond(req, resp, child, self.fields)

    # DELETE

    def on_delete_mail_folder_by_id(self, req, resp, folderid):
        """Delete a mailFolder by ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): target folder ID which should be removed.

        Raises:
            falcon.HTTPNotFound: when folder not found.
        """
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        if not folder:
            raise falcon.HTTPNotFound(description="folder not found")
        self.handle_delete(req, resp, store=store, folder=folder)

    def on_delete_child_folder_by_id(self, req, resp, folderid, childid):
        """Delete a childFolder by ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): parent folder ID.
            childid (str): child folder ID which should be removed.
        """
        parent, child = self._get_child_folder_by_id(req, folderid, childid)
        parent.delete([child])
        self.respond_204(resp)
