# SPDX-License-Identifier: AGPL-3.0-or-later
import codecs

import falcon

from .resource import DEFAULT_TOP, Resource
from .utils import _folder, _server_store, db_get, db_put, experimental


class DeletedFolder(object):
    pass


class FolderImporter:
    def __init__(self):
        self.updates = []
        self.deletes = []

    def update(self, folder):
        self.updates.append(folder)
        db_put(folder.sourcekey, folder.entryid)  # TODO different db?

    def delete(self, folder, flags):
        d = DeletedFolder()
        d.entryid = db_get(folder.sourcekey)
        d.container_class = 'IPF.Note'  # TODO
        self.deletes.append(d)


class FolderResource(Resource):
    fields = {
        'id': lambda folder: folder.entryid,
    }

    @experimental
    def handle_delete(self, req, resp, store, folder):
        store.delete(folder)
        self.respond_204(resp)

    def on_delete(self, req, resp, userid=None, folderid=None):
        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid)

        if not folder:
            raise falcon.HTTPNotFound(description="folder not found")

        self.handle_delete(req, resp, store=store, folder=folder)

    @experimental
    def delta(self, req, resp, store):  # TODO contactfolders, calendars.. use restriction?
        args = self.parse_qs(req)
        token = args['$deltatoken'][0] if '$deltatoken' in args else None
        importer = FolderImporter()
        newstate = store.subtree.sync_hierarchy(importer, token)
        changes = [(o, self) for o in importer.updates] + \
            [(o, self.deleted_resource) for o in importer.deletes]
        changes = [c for c in changes if c[0].container_class in self.container_classes]  # TODO restriction?
        data = (changes, DEFAULT_TOP, 0, len(changes))
        deltalink = b"%s?$deltatoken=%s" % (req.path.encode('utf-8'), codecs.encode(newstate, 'ascii'))

        self.respond(req, resp, data, self.fields, deltalink=deltalink)
