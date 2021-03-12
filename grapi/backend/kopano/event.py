# SPDX-License-Identifier: AGPL-3.0-or-later
import binascii

import dateutil.parser
import falcon
import kopano

from grapi.api.v1.schema import event as event_schema

from .item import ItemResource, get_body, get_email, set_body
from .resource import _date, _start_end, _tzdate, set_date
from .utils import HTTPBadRequest, HTTPNotFound, _folder, experimental

pattern_map = {
    'monthly': 'absoluteMonthly',
    'monthly_rel': 'relativeMonthly',
    'daily': 'daily',
    'weekly': 'weekly',
    'yearly': 'absoluteYearly',
    'yearly_rel': 'relativeYearly',
}
pattern_map_rev = dict((b, a) for (a, b) in pattern_map.items())

range_end_map = {
    'end_date': 'endDate',
    'forever': 'noEnd',
    'count': 'numbered',
}
range_end_map_rev = dict((b, a) for (a, b) in range_end_map.items())

show_as_map = {
    'free': 'free',
    'tentative': 'tentative',
    'busy': 'busy',
    'out_of_office': 'oof',
    'working_elsewhere': 'workingElsewhere',
    'unknown': 'unknown',
}


def recurrence_json(item):
    if isinstance(item, kopano.Item) and item.recurring:
        recurrence = item.recurrence
        # graph outputs some useless fields here, so we do too!
        j = {
            'pattern': {
                'type': pattern_map[recurrence.pattern],
                'interval': recurrence.interval,
                'month': recurrence.month or 0,
                'dayOfMonth': recurrence.monthday or 0,
                'index': recurrence.index or 'first',
                'firstDayOfWeek': recurrence.first_weekday,
            },
            'range': {
                'type': range_end_map[recurrence.range_type],
                'startDate': _date(recurrence.start, False, False),
                'endDate': _date(recurrence.end, False, False) if recurrence.range_type != 'no_end' else '0001-01-01',
                'numberOfOccurrences': recurrence.count if recurrence.range_type == 'occurrence_count' else 0,
                'recurrenceTimeZone': "",  # TODO: get recurrence timezone from recurrence blob (PidLidAppointmentTimeZoneDefinitionRecur)
            },
        }
        if recurrence.weekdays:
            j['pattern']['daysOfWeek'] = recurrence.weekdays
        return j


def recurrence_set(item, arg):
    # TODO order of setting recurrence attrs shouldn't matter

    if arg is None:
        item.recurring = False  # TODO pyko checks.. cleanup?
    else:
        item.recurring = True
        rec = item.recurrence

        if 'recurrenceTimezone' in arg['range']:
            item.timezone = arg['range']['recurrenceTimeZone']

        rec.pattern = pattern_map_rev[arg['pattern']['type']]
        rec.interval = arg['pattern']['interval']
        if 'daysOfWeek' in arg['pattern']:
            rec.weekdays = arg['pattern']['daysOfWeek']
        if 'dayOfMonth' in arg['pattern']:
            rec.monthday = arg['pattern']['dayOfMonth']
        if 'index' in arg['pattern']:
            rec.index = arg['pattern']['index']

        rec.range_type = range_end_map_rev[arg['range']['type']]
        if 'numberOfOccurrences' in arg['range']:
            rec.count = arg['range']['numberOfOccurrences']

        # TODO don't use hidden vars
        rec.start = dateutil.parser.parse(arg['range']['startDate'])
        if arg['range']['type'] == 'noEnd':
            rec.end = dateutil.parser.parse('31-12-4500')
        else:
            rec.end = dateutil.parser.parse(arg['range']['endDate'])

        rec._save()


def attendees_json(item):
    result = []
    for attendee in item.attendees():
        address = attendee.address
        data = {
            # TODO map response field names
            'status': {'response': attendee.response or 'None', 'time': _date(attendee.response_time)},
            'type': attendee.type_,
        }
        data.update(get_email(address))
        result.append(data)
    return result


def location_json(item):
    if not item.location or item.location.strip() == '':
        return None

    return {
        'displayName': item.location,
        'locationType': 'default',
    }


def location_set(item, arg):
    # TODO(longsleep): Support storing locationType.
    setattr(item, 'location', arg.get('displayName', ''))


def attendees_set(item, arg):
    for a in arg:
        email = a['emailAddress']
        addr = '%s <%s>' % (email.get('name', email['address']), email['address'])
        item.create_attendee(a['type'], addr)


def responsestatus_json(item):
    # 8.7.x does not have response_status attribute, so we must check.
    response_status = item.response_status if hasattr(item, 'response_status') else 'None'
    response_time = _date(item.replytime) if hasattr(item, 'replytime') else '0001-01-01T00:00:00Z'
    return {
        'response': response_status,
        'time': response_time,
    }


def event_type(item):
    if item.recurring:
        if isinstance(item, kopano.Occurrence):
            if item.exception:
                return 'exception'
            else:
                return 'occurrence'
        else:
            return 'seriesMaster'
    else:
        return 'singleInstance'


def event_field_setter(event, attr_name, value):
    """Event field setter.

    Args:
        event (Event): event object.
        attr_name (str): attribute name.
        value (Any): attribute's value.

    Raises:
        AttributeError: invalid attribute for an event.
    """
    if hasattr(event, attr_name):
        setattr(event, attr_name, value)
    else:
        raise AttributeError("invalid event attribute: %s" % attr_name)


class EventResource(ItemResource):
    fields = ItemResource.fields.copy()
    fields.update({
        'id': lambda item: item.eventid,
        'subject': lambda item: item.subject,
        'recurrence': recurrence_json,
        'start': lambda req, item: _tzdate(item.start, item.tzinfo, req),
        'end': lambda req, item: _tzdate(item.end, item.tzinfo, req),
        'location': location_json,
        'importance': lambda item: item.urgency,
        'sensitivity': lambda item: item.sensitivity,
        'hasAttachments': lambda item: item.has_attachments,
        'body': lambda req, item: get_body(req, item),
        'isReminderOn': lambda item: item.reminder,
        'reminderMinutesBeforeStart': lambda item: item.reminder_minutes,
        'attendees': lambda item: attendees_json(item),
        'bodyPreview': lambda item: item.body_preview,
        'isAllDay': lambda item: item.all_day,
        'showAs': lambda item: show_as_map[item.show_as],
        'seriesMasterId': lambda item: item.item.eventid if item.recurring and isinstance(item, kopano.Occurrence) else None,
        'type': lambda item: event_type(item),
        'responseRequested': lambda item: item.response_requested,
        'iCalUId': lambda item: kopano.hex(kopano.bdec(item.icaluid)) if item.icaluid else None,  # graph uses hex!?
        'organizer': lambda item: get_email(item.from_),
        'isOrganizer': lambda item: item.from_.email == item.sender.email,
        'isCancelled': lambda item: item.canceled,
        'responseStatus': lambda item: responsestatus_json(item),
        # 8.7.x does not have onlinemeetingurl attribute, so we must check if its there for compatibility
        'onlineMeetingUrl': lambda item: item.onlinemeetingurl if hasattr(item, 'onlinemeetingurl') else ''
    })

    set_fields = {
        'subject': lambda item, arg: setattr(item, 'subject', arg),
        'location': lambda item, arg: location_set(item, arg),
        'body': set_body,
        'start': lambda item, arg: set_date(item, 'start', arg),
        'end': lambda item, arg: set_date(item, 'end', arg),
        'attendees': lambda item, arg: attendees_set(item, arg),
        'recurrence': recurrence_set,
        'isAllDay': lambda item, arg: setattr(item, 'all_day', arg),
        'isReminderOn': lambda item, arg: setattr(item, 'reminder', arg),
        'categories': lambda item, arg: event_field_setter(item, 'categories', arg),
        'reminderMinutesBeforeStart': lambda item, arg: setattr(item, 'reminder_minutes', arg),
        # 8.7.x does not have onlinemeetingurl attribute, so we must check if its there for compatibility
        'onlineMeetingUrl': lambda item, arg: setattr(item, 'onlinemeetingurl', arg) if hasattr(item, 'onlinemeetingurl') else None,
    }

    # TODO delta functionality seems to include expanding recurrences!? check with MSGE

    # GET

    @staticmethod
    def get_event(folder, eventid):
        try:
            return folder.event(eventid)
        except (binascii.Error, kopano.errors.ArgumentError):
            raise HTTPBadRequest('Event id is malformed')
        except kopano.errors.NotFoundError:
            raise HTTPNotFound(description='Item not found')

    def _get_event_instances(self, req, resp, folderid, eventid):
        start, end = _start_end(req)

        server, store, userid = req.context.server_store
        folder = _folder(store, folderid)
        event = self.get_event(folder, eventid)

        def yielder(**kwargs):
            for occ in event.occurrences(start, end, **kwargs):
                yield occ
        data = self.generator(req, yielder)
        self.respond(req, resp, data)

    def on_get_instances_by_folderid(self, req, resp, folderid, itemid):
        self._get_event_instances(req, resp, folderid, itemid)

    def on_get_instances(self, req, resp, itemid):
        self._get_event_instances(req, resp, "calendar", itemid)

    def handle_get(self, req, resp, event):
        self.respond(req, resp, event)

    @experimental
    def on_get_events(self, req, resp):
        store = req.context.server_store[1]
        calendar = store.calendar
        data = self.generator(req, calendar.items, calendar.count)
        self.respond(req, resp, data, EventResource.fields)

    def on_get_by_folderid(self, req, resp, folderid):
        """Get events of a specific folder."""
        _, store, _ = req.context.server_store
        folder = store.folder(folderid)
        store.calendar = folder
        data = self.generator(req, store.calendar.items, store.calendar.count)
        self.respond(req, resp, data, EventResource.fields)

    def on_get_by_eventid(self, req, resp, itemid):
        store = req.context.server_store[1]
        folder = _folder(store, "calendar")
        event = self.get_event(folder, itemid)
        self.respond(req, resp, event, self.fields)

    def on_get_by_folderid_eventid(self, req, resp, folderid, itemid):
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        event = self.get_event(folder, itemid)
        self.respond(req, resp, event, self.fields)

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None):
        raise HTTPBadRequest("Unsupported in event")

    # POST

    def _create_event(self, req, resp, folderid):
        """Create an events.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the event be created in.

        Raises:
            HTTPBadRequest: invalid argument error or request has empty payload.
        """
        if not req.content_length:
            raise HTTPBadRequest("request has empty payload")
        fields = req.context.json_data
        self.validate_json(event_schema.create_schema_validator, fields)

        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        try:
            item = self.create_message(folder, fields, EventResource.set_fields)
        except kopano.errors.ArgumentError as e:
            raise HTTPBadRequest("Invalid argument error '{}'".format(e))
        if fields.get('attendees', None):
            # NOTE(longsleep): Sending can fail with NO_ACCCESS if no permission to outbox.
            item.send()
        self.respond(req, resp, item, EventResource.fields)

    @experimental
    def on_post_events(self, req, resp):
        """Handle POST request to create event in the "calendar" folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        self._create_event(req, resp, "calendar")

    @experimental
    def on_post_by_folderid(self, req, resp, folderid):
        """Handle POST request to create an event in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the event be created in.
        """
        self._create_event(req, resp, folderid)

    def _accept_event(self, req, resp, folderid, eventid):
        fields = req.context.json_data
        self.validate_json(event_schema.action_schema_validator, fields)
        _ = req.context.i18n.gettext
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        item = self.get_event(folder, eventid)
        item.accept(comment=fields.get('comment'), respond=(fields.get('sendResponse', True)), subject_prefix=_("Accepted"))
        resp.status = falcon.HTTP_202

    def on_post_accept_event_by_folderid(self, req, resp, folderid, itemid):
        self._accept_event(req, resp, folderid, itemid)

    def on_post_accept_event(self, req, resp, itemid):
        self._accept_event(req, resp, "calendar", itemid)

    def handle_post_tentativelyAccept(self, req, resp, fields, item):
        _ = req.context.i18n.gettext
        self.validate_json(event_schema.action_schema_validator, fields)
        item.accept(comment=fields.get('comment'), tentative=True, respond=(fields.get('sendResponse', True)), subject_prefix=_("Tentatively accepted"))
        resp.status = falcon.HTTP_202

    def _decline_event(self, req, resp, folderid, itemid):
        fields = req.context.json_data
        self.validate_json(event_schema.action_schema_validator, fields)
        _ = req.context.i18n.gettext
        store = req.context.server_store[1]
        self.validate_json(event_schema.action_schema_validator, fields)
        folder = _folder(store, folderid)
        item = self.get_event(folder, itemid)
        item.decline(comment=fields.get('comment'), respond=(fields.get('sendResponse', True)), subject_prefix=_("Declined"))
        resp.status = falcon.HTTP_202

    def on_post_decline_event_by_folderid(self, req, resp, folderid, itemid):
        self._decline_event(req, resp, folderid, itemid)

    def on_post_decline_event(self, req, resp, itemid):
        self._decline_event(req, resp, "calendar", itemid)

    def on_post(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        handler = None

        if method == 'tentativelyAccept':
            handler = self.handle_post_tentativelyAccept

        elif method:
            raise HTTPBadRequest("Unsupported event segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in event")

        server, store, userid = req.context.server_store
        folder = _folder(store, folderid or 'calendar')
        item = self.get_event(folder, itemid)
        fields = req.context.json_data
        handler(req, resp, fields=fields, item=item)

    # PATCH

    def _update_event(self, req, resp, folderid, itemid):
        """Update an event.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the event exists in.
            itemid (str): item/event ID which should be updated.
        """
        fields = req.context.json_data
        store = req.context.server_store[1]
        folder = _folder(store, folderid)
        item = self.get_event(folder, itemid)

        for field, value in fields.items():
            if field in self.set_fields:
                self.set_fields[field](item, value)

        self.respond(req, resp, item, self.fields)

    def on_patch_by_eventid(self, req, resp, itemid):
        """Handle PATCH request for a specific event in 'calendar' folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): item/event ID which should be updated.
        """
        self._update_event(req, resp, "calendar", itemid)

    def on_patch_by_folderid_eventid(self, req, resp, folderid, itemid):
        """Handle PATCH request for a specific event in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the event exists in.
            itemid (str): item/event ID which should be updated.
        """
        self._update_event(req, resp, folderid, itemid)

    # DELETE

    def _delete_event(self, req, resp, folderid, itemid):
        """Delete an event.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the event exists in.
            itemid (str): item/event ID which should be deleted.
        """
        server, store, userid = req.context.server_store
        folder = _folder(store, folderid)
        event = self.get_event(folder, itemid)

        # If meeting is organised, sent cancellation
        if self.fields['isOrganizer'](event):
            event.cancel()
            event.send()

        folder.delete(event)
        self.respond_204(resp)

    def on_delete_by_eventid(self, req, resp, itemid):
        """Handle DELETE request for a specific event in 'calendar' folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            itemid (str): item/event ID which should be deleted.
        """
        self._delete_event(req, resp, "calendar", itemid)

    def on_delete_by_folderid_eventid(self, req, resp, folderid, itemid):
        """Handle DELETE request for a specific event in a specific folder.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
            folderid (str): folder ID which the event exists in.
            itemid (str): item/event ID which should be deleted.
        """
        self._delete_event(req, resp, folderid, itemid)
