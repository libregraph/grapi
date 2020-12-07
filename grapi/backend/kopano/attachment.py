"""Attachment resource module."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
from enum import Enum
from functools import partial

import falcon

from . import message
from .resource import DEFAULT_TOP, Resource, _date
from .schema import (file_attachment_schema, item_attachment_schema,
                     reference_attachment_schema)
from .utils import HTTPBadRequest, _folder, _item, experimental


class AttachmentType(Enum):
    """OData attachment type."""

    FILE = 1
    ITEM = 2
    REFERENCE = 3


class FolderType(Enum):
    """Folder type."""

    FOLDER = 1
    CALENDAR = 2


def get_attachment_type(odata_type):
    """Detect attachment type.

    Args:
        odata_type (str): request odata type.

    Returns:
        AttachmentType: detected attachment type.

    Raises:
        ValueError: invalid odata type.
    """
    if odata_type == "#microsoft.graph.fileAttachment":
        return AttachmentType.FILE
    elif odata_type == "#microsoft.graph.itemAttachment":
        return AttachmentType.ITEM
    elif odata_type == "#microsoft.graph.referenceAttachment":
        return AttachmentType.REFERENCE
    raise ValueError("invalid odata type")


def get_folder_type(url):
    """Detect folder type based on URL.

    It's useful when we don't have any folder id in the URL.
    e.g. /me/events/<itemid>/attachments

    Args:
        url (str): request URL.

    Returns:
        FolderType: detected folder type.

    Raises:
        ValueError: invalid folder type.
    """
    if "/calendar" in url or "/events/" in url:
        return FolderType.CALENDAR
    elif "/messages/" in url or "/mailFolders/" in url:
        return FolderType.FOLDER
    raise ValueError("invalid folder type")


def get_default_folder(req):
    """Return default folder based on request.

    Args:
        req (Request): Falcon request object.

    Returns:
        Tuple[FolderType,Folder]: folder type with default folder
            based on the request (e.g. inbox or calendar).

    Raises:
        HTTPNotFound: folder type not found
    """
    store = req.context.server_store[1]
    try:
        folder_type = get_folder_type(req.path)
    except ValueError:
        raise falcon.HTTPNotFound(description="folder type not found")

    if folder_type == FolderType.CALENDAR:
        return folder_type, store.calendar
    elif folder_type == FolderType.FOLDER:
        return folder_type, store.inbox
    raise falcon.HTTPNotFound(description="folder type not found")


def get_item(req, itemid):
    """Get item based on request.

    Args:
        req (Request): Falcon request object.
        itemid (str): item ID (e.g. message ID, event ID).

    Returns:
        Item: instance of an item based on the request.

    Raises:
        HTTPNotFound: folder type not found
    """
    folder_type, folder = get_default_folder(req)
    if folder_type == FolderType.FOLDER:
        return _item(folder, itemid)
    elif folder_type == FolderType.CALENDAR:
        return folder.event(itemid)
    raise falcon.HTTPNotFound(description="folder type not found")


def get_item_by_folder(req, folder, itemid):
    """Get item by a folder.

    Args:
        req (Request): Falcon request object.
        folder (Folder): instance of a folder.
        itemid (str): item ID (e.g. message ID, event ID).

    Returns:
        Item: instance of an item based on the request.

    Raises:
        HTTPNotFound: folder type not found
    """
    folder_type = get_default_folder(req)[0]
    if folder_type == FolderType.FOLDER:
        return _item(folder, itemid)
    elif folder_type == FolderType.CALENDAR:
        return folder.event(itemid)
    raise falcon.HTTPNotFound(description="folder type not found")


def binary_response(resp, attachment):
    """Prepare binary response.

    Args:
        resp (Response): Falcon response object.
        attachment (Attachment): attachment object.
    """
    resp.content_type = attachment.mimetype
    resp.data = attachment.data


def response_fields(attachment):
    """Prepare response fields.

    Args:
        attachment (Attachment): attachment object.

    Returns:
        dict: fields of an attachment-resource class.
    """
    if attachment.embedded:
        return ItemAttachmentResource.fields
    return FileAttachmentResource.fields


@experimental
class AttachmentResource(Resource):
    """Attachment resource of all containers."""

    fields = {
        'id': lambda attachment: attachment.entryid,
        'lastModifiedDateTime': lambda attachment: _date(attachment.last_modified),
        'size': lambda attachment: attachment.size,
    }

    # GET

    def on_get_by_id(self, req, resp, itemid, attachmentid=None):
        """Return attachment(s) by itemid with or without attachmentid.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): item ID (e.g. message ID or event ID).
            attachmentid (str): attachment ID which is related to the item. Defaults to None.
        """
        item = get_item(req, itemid)
        self._response_attachments(req, resp, item, attachmentid)

    def on_get_binary_by_id(self, req, resp, itemid, attachmentid):
        """Return attachment's raw by itemid and attachmentid.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): item ID (e.g. message ID or event ID).
            attachmentid (str): attachment ID which is related to the item.
        """
        item = get_item(req, itemid)
        binary_response(resp, item.attachment(attachmentid))

    def on_get_in_folder_by_id(self, req, resp, folderid, itemid, attachmentid=None):
        """Return attachment by itemid with or without attachmentid in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the item exists in.
            itemid (str): item ID (e.g. message ID or event ID).
            attachmentid (str): attachment ID which is related to the item. Defaults to None.
        """
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        item = get_item_by_folder(req, folder, itemid)
        self._response_attachments(req, resp, item, attachmentid)

    def on_get_binary_in_folder_by_id(self, req, resp, folderid, itemid, attachmentid):
        """Return attachment's raw by itemid and attachmentid in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the item exists in.
            itemid (str): item ID (e.g. message ID or event ID).
            attachmentid (str): attachment ID which is related to the item.
        """
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        item = get_item_by_folder(req, folder, itemid)
        binary_response(resp, item.attachment(attachmentid))

    def _response_attachments(self, req, resp, item, attachmentid=None):
        """Response attachments by itemid with or without attachment ID.

        Todo:
            to return list of attachments, we're hardcoded fields of FileAttachmentResource
            while it should be more dynamic to support other types like reference or item
            attachments as well. (issue: KC-1914)

         Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            item (Item): instance of an item.
            attachmentid (str): attachment ID which is related to the item. Defaults to None.
        """
        response = partial(self.respond, req, resp)
        if attachmentid is None:
            attachments = list(item.attachments(embedded=True))
            response(
                (attachments, DEFAULT_TOP, 0, len(attachments)),
                FileAttachmentResource.fields
            )
        else:
            attachment = item.attachment(attachmentid)
            response(attachment, response_fields(attachment))

    # POST

    def on_post_by_id(self, req, resp, itemid, attachmentid=None):
        """Add attachment by itemid.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): item ID (e.g. message ID or event ID).
            attachmentid (str): attachment ID, this parameter must be None as in a POST
                request we don't have the attachmentid. Defaults to None.

        Raises:
            HTTPNotFound: when attachmentid has value.
        """
        if attachmentid:
            raise falcon.HTTPNotFound()
        item = get_item(req, itemid)
        self._add_attachments(req, resp, item)

    def on_post_in_folder_by_id(self, req, resp, folderid, itemid, attachmentid=None):
        """Add attachment by itemid in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the item exists in.
            itemid (str): item ID (e.g. message ID or event ID).
            attachmentid (str): attachment ID, this parameter must be None as in a POST
                request we don't have the attachmentid. Defaults to None.

        Raises:
            HTTPNotFound: when attachmentid has value.
        """
        if attachmentid:
            raise falcon.HTTPNotFound()
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        item = get_item_by_folder(req, folder, itemid)
        self._add_attachments(req, resp, item)

    def _add_attachments(self, req, resp, item):
        """Add attachments for an event in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            item (Item): item instance (e.g. message or event).

        Raises:
            HTTPBadRequest: unsupported attachment.
        """
        fields = self.load_json(req)
        odata_type = fields.get('@odata.type', None)
        try:
            attachment_type = get_attachment_type(odata_type)
        except ValueError:
            raise HTTPBadRequest("Unsupported attachment @odata.type: '%s'" % odata_type)

        if attachment_type == AttachmentType.FILE:
            self.validate_json(file_attachment_schema, fields)
            att = item.create_attachment(fields['name'], base64.urlsafe_b64decode(fields['contentBytes']))
            self.respond(req, resp, att, self.fields)
            resp.status = falcon.HTTP_201
        elif attachment_type == AttachmentType.ITEM:
            self.validate_json(fields, item_attachment_schema)
            raise falcon.HTTPNotAcceptable(description="itemAttachment is not supported yet")
        elif attachment_type == AttachmentType.REFERENCE:
            self.validate_json(fields, reference_attachment_schema)
            raise falcon.HTTPNotAcceptable(description="referenceAttachment is not supported yet")

    # DELETE

    def on_delete_by_id(self, req, resp, itemid, attachmentid):
        """Delete an attachment from an item.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): item ID (e.g. message ID or event ID).
            attachmentid (str): attachment ID which is related to the item.
        """
        item = get_item(req, itemid)
        item.delete(item.attachment(attachmentid))
        self.respond_204(resp)

    def on_delete_in_folder_by_id(self, req, resp, folderid, itemid, attachmentid):
        """Delete an attachment from an item in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the item exists in.
            itemid (str): item ID (e.g. message ID or event ID).
            attachmentid (str): attachment ID which is related to the item.
        """
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        item = get_item_by_folder(req, folder, itemid)
        item.delete(item.attachment(attachmentid))
        self.respond_204(resp)


class FileAttachmentResource(AttachmentResource):
    """File attachment resource for all entities."""

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
    """Item attachment resource for all entities."""

    fields = AttachmentResource.fields.copy()
    fields.update({
        '@odata.type': lambda attachment: '#microsoft.graph.itemAttachment',
        'contentType': lambda attachment: 'message/rfc822',
        'name': lambda attachment: attachment.item.subject,  # TODO faster? attachment.something?
    })

    expansions = {
        'microsoft.graph.itemAttachment/item': lambda attachment: (attachment.item, message.EmbeddedMessageResource),
    }
