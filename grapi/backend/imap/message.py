# SPDX-License-Identifier: AGPL-3.0-or-later

import json

from . import utils, Resource

class MessageResource(Resource):
    fields = {
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
    }

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        M = utils.login()
        M.select()
        itemid = itemid.encode('ascii')
        typ, data = M.fetch(itemid, '(RFC822)')
        data = utils.convert_message(itemid, data)
        utils.logoff(M)

        resp.content_type = 'application/json'
        resp.body = json.dumps(data, indent=2) # TODO stream

