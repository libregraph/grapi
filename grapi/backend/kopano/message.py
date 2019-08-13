# SPDX-License-Identifier: AGPL-3.0-or-later
import base64

import falcon

from .utils import (
    _server_store, _folder, _item, HTTPBadRequest, experimental
)
from .resource import (
    DEFAULT_TOP, _date, json
)

from .item import (
    ItemResource, get_body, set_body, get_email, get_attachments,
)

def set_torecipients(item, arg):
    addrs = []
    for a in arg:
        a = a['emailAddress']
        addrs.append('%s <%s>' % (a.get('name', a['address']), a['address']))
    item.to = ';'.join(addrs)

class DeletedMessageResource(ItemResource):
    fields = {
        '@odata.type': lambda item: '#microsoft.graph.message', # TODO
        'id': lambda item: item.entryid,
        '@removed': lambda item: {'reason': 'deleted'} # TODO soft deletes
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
        'attachments': lambda message: (message.attachments, FileAttachmentResource), # TODO embedded
    }

    def handle_get(self, req, resp, store, folder, itemid):
        if itemid == 'delta': # TODO move to MailFolder resource somehow?
            self._handle_get_delta(req, resp, store=store, folder=folder)
        else:
            self._handle_get_with_itemid(req, resp, store=store, folder=folder, itemid=itemid)

    def _handle_get_delta(self, req, resp, store, folder):
        req.context['deltaid'] = '{itemid}'
        self.delta(req, resp, folder=folder)

    def _handle_get_with_itemid(self, req, resp, store, folder, itemid):
        item = _item(folder, itemid)
        self.respond(req, resp, item)

    def handle_get_attachments(self, req, resp, store, folder, itemid):
        item = _item(folder, itemid)
        attachments = list(get_attachments(item))
        data = (attachments, DEFAULT_TOP, 0, len(attachments))
        self.respond(req, resp, data)

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if not method:
            handler = self.handle_get

        elif method == 'attachments':
            handler = self.handle_get_attachments

        elif method:
            raise HTTPBadRequest("Unsupported message segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in message")

        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'inbox') # TODO all folders?
        handler(req, resp, store=store, folder=folder, itemid=itemid)

    def handle_post_createReply(self, req, resp, store, folder, item):
        self.respond(req, resp, item.reply())
        resp.status = falcon.HTTP_201

    def handle_post_createReplyAll(self, req, resp, store, folder, item):
        self.respond(req, resp, item.reply(all=True))
        resp.status = falcon.HTTP_201

    def handle_post_attachments(self, req, resp, store, folder, item):
        fields = self.load_json(req)
        odataType = fields.get('@odata.type', None)
        if odataType == '#microsoft.graph.fileAttachment': # TODO other types
            att = item.create_attachment(fields['name'], base64.urlsafe_b64decode(fields['contentBytes']))
            self.respond(req, resp, att, FileAttachmentResource.fields)
            resp.status = falcon.HTTP_201
        else:
            raise HTTPBadRequest("Unsupported attachment @odata.type: '%s'" % odataType)

    def handle_post_copy(self, req, resp, store, folder, item):
        self._handle_post_copyOrMove(req, resp, store=store, folder=folder, item=item)

    def handle_post_move(self, req, resp, store, folder, item):
        self._handle_post_copyOrMove(req, resp, store=store, folder=folder, item=item, move=True)

    def _handle_post_copyOrMove(self, req, resp, store, item, move=False):
        fields = self.load_json(req)
        to_folder = store.folder(entryid=fields['destinationId'].encode('ascii')) # TODO ascii?
        if not move:
            item = item.copy(to_folder)
        else:
            item = item.move(to_folder)

    def on_post(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if method == 'createReply':
            handler = self.handle_post_creatReply

        elif method == 'createReplyAll':
            handler = self.handle_post_createReplyAll

        elif method == 'attachments':
            handler = self.handle_post_attachments

        elif method == 'copy':
            handler = self.handle_post_copy

        elif method == 'move':
            handler = self.handle_post_move

        elif method == 'send':
            item.send()
            resp.status = falcon.HTTP_202

        elif method:
            raise HTTPBadRequest("Unsupported message segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in message")

        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'inbox') # TODO all folders?
        item = _item(folder, itemid)
        handler(req, resp, store=store, folder=folder, item=item)

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

        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'inbox') # TODO all folders?
        handler(req, resp, store=store, folder=folder, itemid=itemid)

    def handle_delete(self, req, resp, store, itemid):
        item = _item(store, itemid)

        store.delete(item)

        self.respond_204(resp)

    def on_delete(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if not method:
            handler = self.handle_delete

        else:
            raise HTTPBadRequest("Unsupported message segment '%s'" % method)

        server, store, userid = _server_store(req, userid, self.options)
        handler(req, resp, store=store, itemid=itemid)

class EmbeddedMessageResource(MessageResource):
    fields = MessageResource.fields.copy()
    fields.update({
        'id': lambda item: '',
    })
    del fields['@odata.etag'] # TODO check MSG
    del fields['parentFolderId']
    del fields['changeKey']

from .attachment import (
    FileAttachmentResource
)
