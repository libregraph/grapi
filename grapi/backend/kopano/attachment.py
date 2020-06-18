# SPDX-License-Identifier: AGPL-3.0-or-later
import base64

from . import message
from .resource import Resource, _date
from .utils import _folder, _item, _server_store, experimental


@experimental
class AttachmentResource(Resource):
    fields = {
        'id': lambda attachment: attachment.entryid,
        'lastModifiedDateTime': lambda attachment: _date(attachment.last_modified),
        'size': lambda attachment: attachment.size,
    }

    # TODO to ItemAttachmentResource
    expansions = {
        'microsoft.graph.itemAttachment/item': lambda attachment: (attachment.item, message.EmbeddedMessageResource),
    }

    def handle_get(self, req, resp, store, server, userid, folderid, itemid, eventid, attachmentid, method):
        if folderid:
            folder = _folder(store, folderid)
        elif eventid:
            folder = store.calendar
        elif itemid:
            folder = store.inbox  # TODO messages from all folders?

        if eventid:
            item = folder.event(eventid)  # TODO like _item
        elif itemid:
            item = _item(folder, itemid)

        data = item.attachment(attachmentid)

        if method == '$value':  # TODO graph doesn't do this?
            self._handle_get_value(req, resp, data=data)
        else:
            self._handle_get_fields(req, resp, data=data)

    def _handle_get_value(self, req, resp, data):
        resp.content_type = data.mimetype
        resp.data = data.data

    def _handle_get_fields(self, req, resp, data):
        if data.embedded:
            all_fields = ItemAttachmentResource.fields  # TODO to sub resource
        else:
            all_fields = FileAttachmentResource.fields
        self.respond(req, resp, data, all_fields=all_fields)

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, eventid=None, attachmentid=None, method=None):
        handler = self.handle_get

        server, store, userid = _server_store(req, userid, self.options)
        handler(req, resp, store=store, server=server, userid=userid, folderid=folderid, itemid=itemid, eventid=eventid, attachmentid=attachmentid, method=method)

    def handle_delete(self, req, resp, store, server, userid, folderid, itemid, eventid, attachmentid, method):
        if folderid:  # TODO same code above
            folder = _folder(store, folderid)
        elif eventid:
            folder = store.calendar
        elif itemid:
            folder = store.inbox  # TODO messages from all folders?

        if eventid:
            item = folder.event(eventid)  # TODO like _item
        elif itemid:
            item = _item(folder, itemid)

        attachment = item.attachment(attachmentid)
        item.delete(attachment)

        self.respond_204(resp)

    def on_delete(self, req, resp, userid=None, folderid=None, itemid=None, eventid=None, attachmentid=None, method=None):
        handler = self.handle_delete

        server, store, userid = _server_store(req, userid, self.options)
        handler(req, resp, store=store, server=server, userid=userid, folderid=folderid, itemid=itemid, eventid=eventid, attachmentid=attachmentid, method=method)


class FileAttachmentResource(AttachmentResource):
    fields = AttachmentResource.fields.copy()
    fields.update({
        '@odata.type': lambda attachment: '#microsoft.graph.fileAttachment',
        'name': lambda attachment: attachment.name,
        'contentBytes': lambda attachment: base64.urlsafe_b64encode(attachment.data).decode('ascii'),
        'isInline': lambda attachment: attachment.inline,
        'contentType': lambda attachment: attachment.mimetype,
        'contentId': lambda attachment: attachment.content_id,
        'contentLocation': lambda attachment: attachment.content_location,
    })


class ItemAttachmentResource(AttachmentResource):
    fields = AttachmentResource.fields.copy()
    fields.update({
        '@odata.type': lambda attachment: '#microsoft.graph.itemAttachment',
        'contentType': lambda attachment: 'message/rfc822',
        'name': lambda attachment: attachment.item.subject,  # TODO faster? attachment.something?
    })


def get_attachments(item):
    for attachment in item.attachments(embedded=True):
        if attachment.embedded:
            yield (attachment, ItemAttachmentResource)
        else:
            yield (attachment, FileAttachmentResource)
