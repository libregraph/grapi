# SPDX-License-Identifier: AGPL-3.0-or-later
import base64

import falcon

from . import message
from .event import EventResource
from .resource import DEFAULT_TOP, Resource, _date
from .utils import HTTPBadRequest, _folder, _item, experimental


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

    # GET

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

    def _get_attachments(self, req, resp, folderid, eventid):
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        event = EventResource.get_event(folder, eventid)
        attachments = list(event.attachments(embedded=True))
        data = (attachments, DEFAULT_TOP, 0, len(attachments))
        self.respond(req, resp, data, self.fields)

    @experimental
    def on_get_attachments_by_folderid(self, req, resp, folderid, eventid):
        self._get_attachments(req, resp, folderid, eventid)

    @experimental
    def on_get_attachments_by_itemid(self, req, resp, itemid):
        """Handle GET requests of attachments of an item in the "inbox" folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): item ID (e.g. message ID).
        """
        store = req.context.server_store[1]
        item = _item(store.inbox, itemid)
        attachments = list(item.attachments(embedded=True))
        data = (attachments, DEFAULT_TOP, 0, len(attachments))
        self.respond(req, resp, data, self.fields)

    @experimental
    def on_get_attachments_by_eventid(self, req, resp, eventid):
        self._get_attachments(req, resp, "calendar", eventid)

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, eventid=None, attachmentid=None, method=None):
        handler = self.handle_get

        server, store, userid = req.context.server_store
        handler(req, resp, store=store, server=server, userid=userid, folderid=folderid, itemid=itemid, eventid=eventid, attachmentid=attachmentid, method=method)

    # POST

    def _add_attachments(self, req, resp, folder, item):
        """Add attachments for an event in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folder (Folder): folder instance (e.g. Inbox).
            item (Item): item instance (e.g. message or event).

        Raises:
            HTTPBadRequest: unsupported attachment.
        """
        fields = self.load_json(req)
        odata_type = fields.get('@odata.type', None)
        if odata_type == '#microsoft.graph.fileAttachment':
            att = item.create_attachment(fields['name'], base64.urlsafe_b64decode(fields['contentBytes']))
            self.respond(req, resp, att, self.fields)
            resp.status = falcon.HTTP_201
        else:
            raise HTTPBadRequest("Unsupported attachment @odata.type: '%s'" % odata_type)

    @experimental
    def on_post_attachments_by_folderid(self, req, resp, folderid, eventid):
        """Handle POST request for attachments on an event in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the event exists in.
            eventid (str): event ID which need to have attachments.
        """
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        item = self.get_event(folder, eventid)
        self._add_attachments(req, resp, folder, item)

    @experimental
    def on_post_attachments(self, req, resp, eventid):
        """Handle POST request for attachments on an event in "calendar" folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            eventid (str): event ID which need to have attachments.
        """
        store = req.context.server_store[1]
        item = self.get_event(store.calendar, eventid)
        self._add_attachments(req, resp, store.calendar, item)

    @experimental
    def on_post_attachments_by_itemid(self, req, resp, itemid):
        """Handle POST requests of attachments of an item in the "inbox" folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): item ID (e.g. message ID).
        """
        store = req.context.server_store[1]
        item = _item(store.inbox, itemid)
        self._add_attachments(req, resp, store.inbox, item)

    # DELETE

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

        server, store, userid = req.context.server_store
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
