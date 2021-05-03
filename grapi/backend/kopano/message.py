# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon

from grapi.api.v1.schema import message as message_schema

from . import attachment  # import as module since this is a circular import
from .item import ItemResource, get_body, get_email, set_body
from .resource import _date
from .utils import HTTPBadRequest, HTTPNotFound, _folder, _item, experimental


def set_recipients(item, recipients, field="to"):
    """Set recipients field in an item.

    Args:
        item (Item): item object.
        recipients (list): recipients list.
        field (str): item's field name. Defaults to "to".
    """
    addrs = []
    for recipient in recipients:
        email_address = recipient['emailAddress']
        addrs.append(
            '{} <{}>'.format(
                email_address.get('name', email_address['address']),
                email_address['address']
            )
        )
    setattr(item, field, ';'.join(addrs))


def set_user_email(item, attr_name, user_email):
    """Set user email field in an item.

    Args:
        item (Item): item object.
        attr_name (str): item's attribute name.
        user_email (Dict): user email info.
    """
    email_address = user_email['emailAddress']
    attr_value = '{} <{}>'.format(
        email_address.get('name', email_address['address']),
        email_address['address']
    )
    setattr(item, attr_name, attr_value)


def update_attr_value(item, attr_name, value):
    """Update attribute value of an item.

    Args:
        item (Item): item object.
        attr_name (str): item's attribute name.
        value (Any): attribute value.
    """
    setattr(item, attr_name, value)


def get_internet_headers(item):
    """Format the RFC5322 Message Headers as specified by Microsoft Graph

    Args:
        item (Item): item object.
    Returns:
        List: list of headers formatted as dictionary
    """

    headers = item.headers()
    if not headers:
        return {}

    return [{"name": key, "value": value} for key, value in headers.items()]


class DeletedMessageResource(ItemResource):
    fields = {
        '@odata.type': lambda item: '#microsoft.graph.message',  # TODO
        'id': lambda item: item.entryid,
        '@removed': lambda item: {'reason': 'deleted'}  # TODO soft deletes
    }


@experimental
class MessageResource(ItemResource):
    fields = ItemResource.fields.copy()
    fields.update({
        # TODO pyko shortcut for event messages
        # TODO eventMessage resource?
        '@odata.type': lambda item: '#microsoft.graph.eventMessage' if item.message_class.startswith('IPM.Schedule.Meeting.') else None,
        'subject': lambda item: item.subject,
        'body': lambda req, item: get_body(req, item),
        'from': lambda item: get_email(item.from_),
        'sender': lambda item: get_email(item.sender),
        'toRecipients': lambda item: [get_email(to) for to in item.to],
        'ccRecipients': lambda item: [get_email(cc) for cc in item.cc],
        'bccRecipients': lambda item: [get_email(bcc) for bcc in item.bcc],
        'sentDateTime': lambda item: _date(item.sent) if item.sent else None,
        'receivedDateTime': lambda item: _date(item.received) if item.received else None,
        'hasAttachments': lambda item: item.has_attachments,
        'internetMessageId': lambda item: item.messageid,
        'importance': lambda item: item.urgency.title(),
        'parentFolderId': lambda item: item.folder.entryid,
        'conversationId': lambda item: item.conversationid,
        'isRead': lambda item: item.read,
        'isReadReceiptRequested': lambda item: item.read_receipt,
        'isDeliveryReceiptRequested': lambda item: item.read_receipt,
        'replyTo': lambda item: [get_email(to) for to in item.replyto],
        'bodyPreview': lambda item: item.body_preview,
    })

    select_field_map = {
        'internetMessageHeaders': lambda item: get_internet_headers(item),
    }

    set_fields = {
        'subject': lambda item, value: update_attr_value(item, "subject", value),
        'body': set_body,
        'toRecipients': set_recipients,
        'from': lambda item, arg: set_user_email(item, 'from_', arg),
        'sender': lambda item, arg: set_user_email(item, 'sender', arg),
        'isRead': lambda item, value: update_attr_value(item, "read", value),
    }

    deleted_resource = DeletedMessageResource

    relations = {
        'attachments': lambda message: (message.attachments, attachment.FileAttachmentResource),  # TODO embedded
    }

    # GET

    def handle_get(self, req, resp, store, folder, itemid):
        if itemid == 'delta':  # TODO move to MailFolder resource somehow?
            self._handle_get_delta(req, resp, store=store, folder=folder)

    def _handle_get_delta(self, req, resp, store, folder):
        req.context.deltaid = '{itemid}'
        self.delta(req, resp, folder=folder)

    @experimental
    def on_get_messages(self, req, resp):
        """Handle GET request for users' 'messages'.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        _, store, _ = req.context.server_store
        data = self.folder_gen(req, store.inbox)
        self.respond(req, resp, data, MessageResource.fields)

    def on_get_item(self, req, resp, folderid=None, itemid=None):
        """Get a message by folder ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID. Defaults to None.
            itemid (str): message ID. Defaults to None. itemid value is mandatory.

        Raises:
            HTTPNotFound: when itemid is None.

        Note:
            Based on MS Explorer result, it never validate folderid. So, we ignore it.
        """
        if itemid is None:
            raise HTTPNotFound()
        store = req.context.server_store[1]
        item = _item(store, itemid)
        self.respond(req, resp, item)

    def on_get_messages_by_folderid(self, req, resp, folderid):
        store = req.context.server_store[1]
        data = _folder(store, folderid)
        data = self.folder_gen(req, data)
        self.respond(req, resp, data, MessageResource.fields)

    def on_get_value(self, req, resp, folderid=None, itemid=None):
        """Get a message as RFC-2822 by folder ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID. Defaults to None.
            itemid (str): message ID. Defaults to None. itemid value is mandatory.

        Raises:
            HTTPNotFound: when itemid is None.

        Note:
            Based on MS Explorer result, it never validate folderid. So, we ignore it.
        """
        if itemid is None:
            raise HTTPNotFound()
        store = req.context.server_store[1]
        item = _item(store, itemid)
        resp.body = item.eml()
        resp.content_type = "text/plain"

    # POST

    def on_post_createReply(self, req, resp, folderid=None, itemid=None):
        """Handle POST request on 'createReply' action.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID or a well-known folder name which the message resides there.
                For a list of supported well-known folder names, see mailFolder resource type.
                Defaults to None.
            itemid (str): message ID. itemid value is mandatory and it shouldn't be None.
                Defaults to None.
        """

        store = req.context.server_store[1]
        item = _item(store, itemid)
        self.respond(req, resp, item.reply())
        resp.status = falcon.HTTP_201

    def on_post_createReplyAll(self, req, resp, folderid=None, itemid=None):
        """Handle POST request on 'createReplyAll' action.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID or a well-known folder name which the message resides there.
                For a list of supported well-known folder names, see mailFolder resource type.
                Defaults to None.
            itemid (str): message ID. itemid value is mandatory and it shouldn't be None.
                Defaults to None.
        """

        store = req.context.server_store[1]
        item = _item(store, itemid)
        self.respond(req, resp, item.reply(all=True))
        resp.status = falcon.HTTP_201

    def handle_post_send(self, req, resp, store, folder, item):
        item.send()
        resp.status = falcon.HTTP_202

    def _create_message(self, req, resp, folderid):
        """Create a new message in a defined folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID.
        """
        fields = req.context.json_data
        self.validate_json(message_schema.create_schema_validator, fields)

        _, store, _ = req.context.server_store

        folder = _folder(store, folderid)
        item = self.create_message(
            folder,
            fields,
            MessageResource.set_fields,
            message_class="IPM.Note"
        )
        resp.status = falcon.HTTP_201
        self.respond(req, resp, item, MessageResource.fields)

    def on_post_messages(self, req, resp):
        """Handle POST request on messages endpoint.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        self._create_message(req, resp, "drafts")

    def on_post_messages_by_folderid(self, req, resp, folderid):
        """Handle POST request on message endpoint with defined folder ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which message should be created in.
        """
        self._create_message(req, resp, folderid)

    def _handle_copy_or_move(self, req, resp, itemid, is_move):
        """Copy or move item into another folder.

        Args:
            req (Request): Falcon request object.
            req (Response): Falcon response object.
            itemid (str): message ID.
            is_move (bool): True means 'move', False means 'copy'.

        Raises:
            HTTPNotFound: when itemid is None.
        """
        if itemid is None:
            raise HTTPNotFound()
        json_data = req.context.json_data
        self.validate_json(message_schema.move_or_copy_schema_validator, json_data)
        store = req.context.server_store[1]
        item = _item(store, itemid)
        to_folder = _folder(store, json_data["destinationId"])
        if is_move:
            item = item.move(to_folder)
        else:
            item = item.copy(to_folder)
        self.respond(req, resp, item, self.fields)
        resp.status = falcon.HTTP_201

    def on_post_copy(self, req, resp, folderid=None, itemid=None):
        """Handle POST request on 'copy' action.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID or a well-known folder name which the message resides there.
                For a list of supported well-known folder names, see mailFolder resource type.
                Defaults to None.
            itemid (str): message ID. Defaults to None. itemid value is mandatory.

        Note:
            Based on MS Explorer result, it never validate folderid. So, we ignore it.
        """
        self._handle_copy_or_move(req, resp, itemid, False)

    def on_post_move(self, req, resp, folderid=None, itemid=None):
        """Handle POST request on 'move' action.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID or a well-known folder name which the message resides there.
                For a list of supported well-known folder names, see mailFolder resource type.
                Defaults to None.
            itemid (str): message ID. itemid value is mandatory and it shouldn't be None.
                Defaults to None.

        Note:
            Based on MS Explorer result, it never validate folderid. So, we ignore it.
        """
        self._handle_copy_or_move(req, resp, itemid, True)

    def on_post(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if method == 'send':
            handler = self.handle_post_send

        elif method:
            raise HTTPBadRequest("Unsupported message segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in message")

        server, store, userid = req.context.server_store
        folder = _folder(store, folderid or 'inbox')  # TODO all folders?
        item = _item(folder, itemid)
        handler(req, resp, store=store, folder=folder, item=item)

    # PATCH

    def on_patch_item(self, req, resp, folderid=None, itemid=None):
        """Handle PATCH request on a specific message by ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID. Defaults to None.
            itemid (str): message ID. Defaults to None. itemid value is mandatory.

        Raises:
            HTTPNotFound: when itemid is None.

        Note:
            Based on MS Explorer result, it never validate folderid. So, we ignore it.
        """
        if itemid is None:
            raise HTTPNotFound()
        json_data = req.context.json_data
        self.validate_json(message_schema.update_schema_validator, json_data)

        store = req.context.server_store[1]
        item = _item(store, itemid)

        for field, value in json_data.items():
            if field in self.set_fields:
                self.set_fields[field](item, value)

        self.respond(req, resp, item, self.fields)

    # DELETE

    def on_delete_item(self, req, resp, folderid=None, itemid=None):
        """Handle DELETE request on a specific message without defining folder ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID. Defaults to None.
            itemid (str): message ID. Defaults to None. itemid value is mandatory.

        Raises:
            HTTPNotFound: when itemid is None.

        Note:
            Based on MS Explorer result, it never validate folderid. So, we ignore it.
        """
        if itemid is None:
            raise HTTPNotFound()
        store = req.context.server_store[1]
        item = _item(store, itemid)
        store.delete(item)
        self.respond_204(resp)


class EmbeddedMessageResource(MessageResource):
    fields = MessageResource.fields.copy()
    fields.update({
        'id': lambda item: '',
    })
    del fields['@odata.etag']  # TODO check MSG
    del fields['parentFolderId']
    del fields['changeKey']
