# SPDX-License-Identifier: AGPL-3.0-or-later
import falcon

from grapi.api.v1.schema import message as message_schema

from . import attachment  # import as module since this is a circular import
from .item import ItemResource, get_body, get_email, set_body
from .resource import _date
from .utils import HTTPNotFound, _folder, _item, experimental


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
        'categories': lambda item, value: update_attr_value(item, 'categories', value),
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

    def on_get_delta(self, req, resp, folderid=None):
        """Get delta messages sync by folder ID.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID. Defaults to None. folderid value is mandatory

        Raises:
            HTTPNotFound: when folderid is None.
        """
        if folderid is None:
            raise HTTPNotFound()
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        self._handle_get_delta(req, resp, store=store, folder=folder)

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
        folder = _folder(store, folderid)
        items, *items_fields = self.folder_gen(req, folder)
        for item in items:
            if not item.has_proposed_new_time():
                items_fields.append((item, self.fields))
            else:
                items_fields.append((item, EventMessage.fields))
        self.respond(req, resp, items_fields)

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

    def on_post_send(self, req, resp, folderid=None, itemid=None):
        """Handle POST request on 'send' action.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the message resides there. Defaults to None.
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
        item.send()
        resp.status = falcon.HTTP_202

    @experimental
    def on_post_send_mail(self, req, resp):
        """Handle POST request on sendMail.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        json_data = req.context.json_data
        self.validate_json(message_schema.send_mail_schema_validator, json_data)
        store = req.context.server_store[1]
        message = self.create_message(
            store.outbox,
            json_data['message'],
            self.set_fields
        )
        message.send(copy_to_sentmail=json_data.get('saveToSentItems', True))
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


def _get_body(item):
    """Get body."""
    return {
        "content": item.content,
        "contentType": item.content_type,
    }


def _recurrence(item, time_zone):
    """Fetch recurrence from data.

    Args:
        item (Recurrence): recurrence object.
        time_zone (str): item time zone.

    Returns:
        Dict: fetched recurrence data.
    """
    if not item:
        return None
    return {
        "pattern": {
            "@odata.type": "microsoft.graph.recurrencePattern",
            "dayOfMonth": item.monthday,
            "daysOfWeek": item.weekdays,
            "firstDayOfWeek": item.first_weekday,
            "index": item.index,
            "interval": item.interval,
            "month": item.month,
            "type": item.pattern,
        },
        "range": {
            "@odata.type": "microsoft.graph.recurrenceRange",
            "endDate": item.end,
            "numberOfOccurrences": item.count,
            "recurrenceTimeZone": time_zone,
            "startDate": item.start,
            "type": "endDate" if item.range_type == "end_date" else item.range_type,
        },
    }


def _proposed_new_time(item):
    """Fetch proposed new time from data."""
    return {
        "end": {
            "@odata.type": "microsoft.graph.dateTimeTimeZone",
            "end": _date(item.end),
        },
        "start": {
            "@odata.type": "microsoft.graph.dateTimeTimeZone",
            "start": _date(item.end),
        },
    }


def _physical_address(item):
    """Fetch physical address."""
    return {
        "city": item.address.city,
        "countryOrRegion": item.address.countryOrRegion,
        "postalCode": item.address.postalCode,
        "state": item.address.state,
        "street": item.address.street,
    }


def _followup_flag(item):
    """Fetch follow up flag from data."""
    return {
        "completedDateTime": _date(item.completedDateTime, True),
        "dueDateTime": _date(item.dueDateTime, True),
        "flagStatus": item.flagStatus,
        "startDateTime": _date(item.startDateTime, True),
    }


def _meeting_message_type(item):
    """Return meeting message type.

    Todo (mort):
        Port "meeting" prefix into pyko (KC-1947).

    Args:
        item (Item): message item.

    Returns:
        str: meeting message type.
    """
    if item.response_status:
        return "meeting{}".format(item.response_status)
    return None


class EventMessage(MessageResource):
    """Event message resource.

    Todo (mort):
        complete eventMessage fields (KC-1946).
        'flag': lambda item: _followup_flag(item).
        'isDelegated': lambda item: item.is_delegated.
        'isOutOfDate': lambda item: item.is_out_of_date.
        'uniqueBody': lambda item: _get_body(item.unique_body).
        'webLink': lambda item: item.web_link.
    """

    fields = {
        **MessageResource.fields.copy(),
        '@odata.type': '#microsoft.graph.eventMessage',
        'allowNewTimeProposals': lambda item: item.allow_new_time_proposals,
        'conversationIndex': lambda item: item.conversationid,
        'endDateTime': lambda item: _date(item.end, True),
        'interfenceClassification': lambda _: None,
        'internetMessageHeaders': lambda item: item.headers(),
        'isAllDay': lambda item: item.all_day,
        'isDraft': lambda item: True if item.sent else False,
        'location': lambda item: item.location,
        'meetingMessageType': lambda item: _meeting_message_type(item),
        'proposedNewTime': lambda item: _proposed_new_time(item),
        'recurrence': lambda item: _recurrence(item.recurrence, item.tzinfo),
        'responseRequested': lambda item: item.response_requested,
        'startDateTime': lambda item: _date(item.start, True) if item.start else None,
        'type': lambda item: item.type_,
    }
