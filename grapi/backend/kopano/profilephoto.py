# SPDX-License-Identifier: AGPL-3.0-or-later
import logging

import kopano

from .resource import Resource
from .utils import HTTPBadRequest, HTTPNotFound, _folder, _item, experimental


@experimental
class ProfilePhotoResource(Resource):
    fields = {
        '@odata.mediaContentType': lambda photo: photo.mimetype,
        'width': lambda photo: photo.width,
        'height': lambda photo: photo.height,
        'id': lambda photo: ('%dX%d' % (photo.width, photo.height))
    }

    @experimental
    def on_get_photos(self, req, resp):
        # TODO multiple photos?
        server, store, userid = req.context.server_store

        if not userid and req.path.split('/')[-1] != 'users':
            userid = kopano.Store(server=server, mapiobj=server.mapistore).user.userid

        user = server.user(userid=userid)

        def yielder(**kwargs):
            photo = user.photo
            if photo:
                yield photo
        data = self.generator(req, yielder)
        self.respond(req, resp, data, self.fields)

    def handle_get(self, req, resp, store, server, userid, folderid, itemid, photoid, method):
        photo = None

        if userid:
            photo = server.user(userid=userid).photo
        elif itemid:
            folder = _folder(store, folderid or 'contacts')
            photo = _item(folder, itemid).photo
        else:
            userid = kopano.Store(server=server, mapiobj=server.mapistore).user.userid
            photo = server.user(userid=userid).photo

        if not photo:
            raise HTTPNotFound(description="The photo wasn't found")

        if photoid:
            try:
                size = tuple(map(int, photoid.lower().split('x')))
            except ValueError:
                raise HTTPNotFound(description="Invalid photo size - must be wxh")
            if len(size) != 2 or size[0] <= 0 or size[1] <= 0:
                raise HTTPNotFound(description="Invalid photo size - must be wxh")
            try:
                photo = photo.scale(size)
            except NotImplementedError:
                logging.exception('unable to scale profile photo')

        if method == '$value':
            self._handle_get_value(req, resp, photo=photo)
        else:
            self._handle_get_fields(req, resp, photo=photo)

    def _handle_get_value(self, req, resp, photo):
        mimetype = photo.mimetype
        resp.content_type = mimetype and mimetype or 'application/octet-stream'
        resp.data = photo.data

    def _handle_get_fields(self, req, resp, photo):
        self.respond(req, resp, photo)

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, photoid=None, method=None):
        handler = self.handle_get

        server, store, userid = req.context.server_store
        handler(req, resp, store=store, server=server, userid=userid, folderid=folderid, itemid=itemid, photoid=photoid, method=method)

    def on_patch(self, *args, **kwargs):
        self.on_put(*args, **kwargs)

    def handle_put(self, req, resp, item):
        item.set_photo('noname', req.stream.read(), req.get_header('Content-Type'))

    def on_put(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if not method:
            handler = self.handle_put

        else:
            raise HTTPBadRequest("Unsupported profilephoto segment '%s'" % method)

        server, store, userid = req.context.server_store
        folder = _folder(store, folderid or 'contacts')
        item = _item(folder, itemid)

        handler(req, resp, item=item)
