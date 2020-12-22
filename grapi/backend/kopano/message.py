# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon

from . import attachment  # import as module since this is a circular import
from .item import ItemResource, get_body, get_email, set_body
from .resource import _date
from .schema import message_schema
from .utils import HTTPBadRequest, _folder, _item, experimental


def set_torecipients(item, arg):
    addrs = []
    for a in arg:
        a = a['emailAddress']
        addrs.append('%s <%s>' % (a.get('name', a['address']), a['address']))
    item.to = ';'.join(addrs)


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
        'importance': lambda item: item.urgency,
        'parentFolderId': lambda item: item.folder.entryid,
        'conversationId': lambda item: item.conversationid,
        'isRead': lambda item: item.read,
        'isReadReceiptRequested': lambda item: item.read_receipt,
        'isDeliveryReceiptRequested': lambda item: item.read_receipt,
        'replyTo': lambda item: [get_email(to) for to in item.replyto],
        'bodyPreview': lambda item: item.body_preview,
    })

    set_fields = {
        'subject': lambda item, arg: setattr(item, 'subject', arg),
        'body': set_body,
        'toRecipients': set_torecipients,
        'isRead': lambda item, arg: setattr(item, 'read', arg),
    }

    deleted_resource = DeletedMessageResource

    relations = {
        'attachments': lambda message: (message.attachments, attachment.FileAttachmentResource),  # TODO embedded
    }

    # GET

    def handle_get(self, req, resp, store, folder, itemid):
        if itemid == 'delta':  # TODO move to MailFolder resource somehow?
            self._handle_get_delta(req, resp, store=store, folder=folder)
        else:
            self._handle_get_with_itemid(req, resp, store=store, folder=folder, itemid=itemid)

    def _handle_get_delta(self, req, resp, store, folder):
        req.context.deltaid = '{itemid}'
        self.delta(req, resp, folder=folder)

    def _handle_get_with_itemid(self, req, resp, store, folder, itemid):
        item = _item(folder, itemid)
        self.respond(req, resp, item)

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

    def on_get_message_by_itemid(self, req, resp, itemid):
        store = req.context.server_store[1]
        item = _item(store.inbox, itemid)
        self.respond(req, resp, item)

    def on_get_messages_by_folderid(self, req, resp, folderid):
        store = req.context.server_store[1]
        data = _folder(store, folderid)
        data = self.folder_gen(req, data)
        self.respond(req, resp, data, MessageResource.fields)

    # POST

    def handle_post_createReply(self, req, resp, store, folder, item):
        self.respond(req, resp, item.reply())
        resp.status = falcon.HTTP_201

    def handle_post_createReplyAll(self, req, resp, store, folder, item):
        self.respond(req, resp, item.reply(all=True))
        resp.status = falcon.HTTP_201

    def handle_post_copy(self, req, resp, store, folder, item):
        self._handle_post_copyOrMove(req, resp, store=store, item=item)

    def handle_post_move(self, req, resp, store, folder, item):
        self._handle_post_copyOrMove(req, resp, store=store, item=item, move=True)

    def _handle_post_copyOrMove(self, req, resp, store, item, move=False):
        fields = self.load_json(req)
        to_folder = store.folder(entryid=fields['destinationId'].encode('ascii'))  # TODO ascii?
        if not move:
            item = item.copy(to_folder)
        else:
            item = item.move(to_folder)

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
        self.validate_json(message_schema, fields)

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

    def on_post(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if method == 'createReply':
            handler = self.handle_post_createReply

        elif method == 'createReplyAll':
            handler = self.handle_post_createReplyAll

        elif method == 'copy':
            handler = self.handle_post_copy

        elif method == 'move':
            handler = self.handle_post_move

        elif method == 'send':
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

    def handle_patch(self, req, resp, store, folder, itemid):
        item = _item(folder, itemid)
        fields = self.load_json(req)

        for field, value in fields.items():
            if field in self.set_fields:
                self.set_fields[field](item, value)

        self.respond(req, resp, item, MessageResource.fields)

    def on_patch(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if not method:
            handler = self.handle_patch

        else:
            raise HTTPBadRequest("Unsupported message segment '%s'" % method)

        server, store, userid = req.context.server_store
        folder = _folder(store, folderid or 'inbox')  # TODO all folders?
        handler(req, resp, store=store, folder=folder, itemid=itemid)

    # DELETE

    def on_delete_message_by_itemid(self, req, resp, itemid):
        """Handle DELETE request on a specific message without defining folder ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): message ID.
        """
        store = req.context.server_store[1]
        item = _item(store, itemid)
        store.delete(item)
        self.respond_204(resp)

    def on_delete_message_by_folderid(self, req, resp, folderid, itemid):
        """Handle DELETE request on a specific message on a defined folder ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which contains the item ID.
            itemid (str): message ID.

        Note:
            Based on MS Explorer result, it never validate folderid. So, we ignore it.
        """
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
