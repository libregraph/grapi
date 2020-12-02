# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon

from .contact import ContactResource
from .folder import FolderResource
from .utils import HTTPBadRequest, _folder, experimental


class DeletedContactFolderResource(FolderResource):
    fields = {
        '@odata.type': lambda folder: '#microsoft.graph.contactFolder',  # TODO
        'id': lambda folder: folder.entryid,
        '@removed': lambda folder: {'reason': 'deleted'}  # TODO soft deletes
    }


@experimental
class ContactFolderResource(FolderResource):
    fields = FolderResource.fields.copy()
    fields.update({
        'displayName': lambda folder: folder.name,
        'parentFolderId': lambda folder: folder.parent.entryid,
    })

    deleted_resource = DeletedContactFolderResource
    container_classes = ('IPF.Contact',)

    def handle_get_delta(self, req, resp, store, folderid):
        req.context.deltaid = '{folderid}'
        self.delta(req, resp, store)

    def handle_get(self, req, resp, store, folderid):
        folder = _folder(store, folderid)
        self.respond(req, resp, folder, self.fields)

    def handle_get_contacts(self, req, resp, store, folderid):
        folder = _folder(store, folderid)
        data = self.folder_gen(req, folder)
        fields = ContactResource.fields
        self.respond(req, resp, data, fields)

    @experimental
    def on_get_contact_folders(self, req, resp):
        store = req.context.server_store[1]
        data = self.generator(req, store.contact_folders, 0)
        self.respond(req, resp, data, ContactFolderResource.fields)

    def on_get(self, req, resp, userid=None, folderid=None, method=None):
        handler = None

        if folderid == 'delta':
            handler = self.handle_get_delta
        else:
            if not method:
                handler = self.handle_get

            elif method == 'contacts':
                handler = self.handle_get_contafts

            elif method:
                raise HTTPBadRequest("Unsupported contactfolder segment '%s'" % method)

            else:
                raise HTTPBadRequest("Unsupported in contactfolder")

        server, store, userid = req.context.server_store
        handler(req, resp, store=store, folderid=folderid)

    def handle_post_contacts(self, req, resp, store, folderid):
        folder = _folder(store, folderid)
        fields = self.load_json(req)
        item = self.create_message(folder, fields, ContactResource.set_fields)

        self.respond(req, resp, item, ContactResource.fields)
        resp.status = falcon.HTTP_201

    def on_post(self, req, resp, userid=None, folderid=None, method=None):
        handler = None

        if method == 'contacts':
            handler = self.handle_post_contacts

        elif method:
            raise HTTPBadRequest("Unsupported contactfolder segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in contactfolder")

        server, store, userid = req.context.server_store
        handler(req, resp, store=store, folderid=folderid)
