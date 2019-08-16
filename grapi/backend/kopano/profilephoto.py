# SPDX-License-Identifier: AGPL-3.0-or-later
from MAPI.Util import GetDefaultStore
import kopano
import logging

from .utils import (
    _server_store, _folder, _item, experimental, HTTPBadRequest, HTTPNotFound
)
from .resource import Resource


@experimental
class ProfilePhotoResource(Resource):
    fields = {
        '@odata.mediaContentType': lambda photo: photo.mimetype,
        'width': lambda photo: photo.width,
        'height': lambda photo: photo.height,
        'id': lambda photo: ('%dX%d' % (photo.width, photo.height))
    }

    def handle_get(self, req, resp, store, server, userid, folderid, itemid, photoid, method):
        photo = None

        if userid:
            photo = server.user(userid=userid).photo
        elif itemid:
            folder = _folder(store, folderid or 'contacts')
            photo = _item(folder, itemid).photo
        else:
            userid = kopano.Store(server=server, mapiobj=GetDefaultStore(server.mapisession)).user.userid
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

        server, store, userid = _server_store(req, userid, self.options)
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

        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'contacts')
        item = _item(folder, itemid)

        handler(req, resp, item=item)
