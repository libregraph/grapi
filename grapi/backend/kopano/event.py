# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import binascii

import dateutil.parser
import falcon

import kopano

from .utils import (
    _server_store, _folder, HTTPBadRequest
)
from .resource import (
    DEFAULT_TOP, json, _date, _tzdate, set_date, _start_end
)
from .item import (
    ItemResource, get_email, get_body, set_body
)

pattern_map = {
    'monthly': 'absoluteMonthly',
    'monthly_rel': 'relativeMonthly',
    'daily': 'daily',
    'weekly': 'weekly',
    'yearly': 'absoluteYearly',
    'yearly_rel': 'relativeYearly',
}
pattern_map_rev = dict((b,a) for (a,b) in pattern_map.items())

range_end_map = {
    'end_date': 'endDate',
    'forever': 'noEnd',
    'count': 'numbered',
}
range_end_map_rev = dict((b,a) for (a,b) in range_end_map.items())

sensitivity_map = {
    'normal': 'Normal',
    'personal': 'Personal',
    'private': 'Private',
    'confidential': 'Confidential',
}

show_as_map = {
    'free': 'Free',
    'tentative': 'Tentative',
    'busy': 'Busy',
    'out_of_office': 'Oof',
    'working_elsewhere': 'WorkingElsewhere',
    'unknown': 'Unknown',
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
                'startDate': _date(recurrence.start, False, False), # TODO hidden
                'endDate': _date(recurrence.end, False, False) if recurrence.range_type != 'no_end' else '0001-01-01',
                'numberOfOccurrences': recurrence.count if recurrence.range_type == 'occurrence_count' else 0,
                'recurrenceTimeZone': "", # TODO
            },
        }
        if recurrence.weekdays:
            j['pattern']['daysOfWeek'] = recurrence.weekdays
        return j

def recurrence_set(item, arg):
    # TODO order of setting recurrence attrs shouldn't matter

    if arg is None:
        item.recurring = False # TODO pyko checks.. cleanup?
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
            'status': {'response': attendee.response or 'none', 'time': _date(attendee.response_time)},
            'type': attendee.type_,
        }
        data.update(get_email(address))
        result.append(data)
    return result

def attendees_set(item, arg):
    for a in arg:
        email = a['emailAddress']
        addr = '%s <%s>' % (email.get('name', email['address']), email['address'])
        item.create_attendee(a['type'], addr)

def responsestatus_json(item):
    # Compatibility for 8.7.x
    response_status = item.response_status if hasattr(item, 'response_status') else 'None'
    return {
        'response': response_status,
        'time': '0001-01-01T00:00:00Z',
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

class EventResource(ItemResource):
    fields = ItemResource.fields.copy()
    fields.update({
        'id': lambda item: item.eventid,
        'subject': lambda item: item.subject,
        'recurrence': recurrence_json,
        'start': lambda req, item: _tzdate(item.start, item.tzinfo, req),
        'end': lambda req, item: _tzdate(item.end, item.tzinfo, req),
        'location': lambda item: {'displayName': item.location, 'address': {}}, # TODO
        'importance': lambda item: item.urgency,
        'sensitivity': lambda item: sensitivity_map[item.sensitivity],
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
        'iCalUId': lambda item: kopano.hex(kopano.bdec(item.icaluid)) if item.icaluid else None, # graph uses hex!?
        'organizer': lambda item: get_email(item.from_),
        'isOrganizer': lambda item: item.from_.email == item.sender.email,
        'responseStatus': lambda item: responsestatus_json(item),
        # 8.7.x does not have onlinemeetingurl attribute, so we must check if its there for compatibility
        'onlineMeetingUrl': lambda item: item.onlinemeetingurl if hasattr(item, 'onlinemeetingurl') else ''
    })

    set_fields = {
        'subject': lambda item, arg: setattr(item, 'subject', arg),
        'location': lambda item, arg: setattr(item, 'location', arg['displayName']), # TODO
        'body': set_body,
        'start': lambda item, arg: set_date(item, 'start', arg),
        'end': lambda item, arg: set_date(item, 'end', arg),
        'attendees': lambda item, arg: attendees_set(item, arg),
        'recurrence': recurrence_set,
        'isAllDay': lambda item, arg: setattr(item, 'all_day', arg),
        'isReminderOn': lambda item, arg: setattr(item, 'reminder', arg),
        'reminderMinutesBeforeStart': lambda item, arg: setattr(item, 'reminder_minutes', arg),
        # 8.7.x does not have onlinemeetingurl attribute, so we must check if its there for compatibility
        'onlineMeetingUrl': lambda item, arg: setattr(item, 'onlinemeetingurl', arg) if hasattr(item, 'onlinemeetingurl') else None,
    }

    # TODO delta functionality seems to include expanding recurrences!? check with MSGE


    def get_event(self, folder, eventid):
        try:
            return folder.event(eventid)
        except binascii.Error:
            raise HTTPBadRequest('Id is malformed')
        except kopano.errors.NotFoundError:
            raise HTTPBadRequest('Item not found')

    def on_get(self, req, resp, userid=None, folderid=None, eventid=None, method=None):
        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'calendar')
        event = self.get_event(folder, eventid)

        if method == 'attachments':
            attachments = list(event.attachments(embedded=True))
            data = (attachments, DEFAULT_TOP, 0, len(attachments))
            self.respond(req, resp, data, AttachmentResource.fields)

        elif method == 'instances':
            start, end = _start_end(req)
            data = (event.occurrences(start, end), DEFAULT_TOP, 0, 0)
            self.respond(req, resp, data)

        elif method:
            raise HTTPBadRequest("Unsupported segment '%s'" % method)

        else:
            self.respond(req, resp, event)

    def on_post(self, req, resp, userid=None, folderid=None, eventid=None, method=None):
        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'calendar')
        item = self.get_event(folder, eventid)
        fields = json.loads(req.stream.read().decode('utf-8'))

        if method == 'accept':
            item.accept(comment=fields.get('comment'), respond=(fields.get('sendResponse')=='true'))
            resp.status = falcon.HTTP_202

        elif method == 'tentativelyAccept':
            item.accept(comment=fields.get('comment'), tentative=True, respond=(fields.get('sendResponse')=='true'))
            resp.status = falcon.HTTP_202

        elif method == 'decline':
            item.decline(comment=fields.get('comment'), respond=(fields.get('sendResponse')=='true'))
            resp.status = falcon.HTTP_202

        elif method == 'attachments':
            if fields['@odata.type'] == '#microsoft.graph.fileAttachment':
                att = item.create_attachment(fields['name'], base64.urlsafe_b64decode(fields['contentBytes']))
                self.respond(req, resp, att, AttachmentResource.fields)
                resp.status = falcon.HTTP_201

        elif method:
            raise HTTPBadRequest("Unsupported segment '%s'" % method)

    def on_patch(self, req, resp, userid=None, folderid=None, eventid=None, method=None):
        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'calendar')

        item = self.get_event(folder, eventid)

        fields = json.loads(req.stream.read().decode('utf-8'))

        for field, value in fields.items():
            if field in self.set_fields:
                self.set_fields[field](item, value)

        self.respond(req, resp, item, EventResource.fields)

    def on_delete(self, req, resp, userid=None, folderid=None, eventid=None):
        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'calendar')
        event = self.get_event(folder, eventid)
        folder.delete(event)

        self.respond_204(resp)

from .attachment import (
    AttachmentResource
)
