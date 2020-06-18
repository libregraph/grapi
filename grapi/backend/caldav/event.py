# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import codecs
import json

from . import utils, Resource

class EventResource(Resource):
    fields = {
        'id': lambda item: item.eventid,
        'subject': lambda item: item.subject,
        'recurrence': None,  #recurrence_json,
        'start': lambda req, item: _tzdate(item.start, req),
        'end': lambda req, item: _tzdate(item.end, req),
        'location': lambda item: {'displayName': item.location, 'address': {}},  # TODO
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
        'seriesMasterId': lambda item: item.item.eventid if isinstance(item, kopano.Occurrence) else None,
        'type': lambda item: event_type(item),
        'responseRequested': lambda item: item.response_requested,
        'iCalUId': lambda item: kopano.hex(kopano.bdec(item.icaluid)) if item.icaluid else None, # graph uses hex!?
        'organizer': lambda item: get_email(item.from_),
        'isOrganizer': lambda item: item.from_.email == item.sender.email,
    }

    def on_get(self, req, resp, userid=None, folderid=None, eventid=None, method=None):
        calendar = utils.calendar()
        url = codecs.decode(base64.urlsafe_b64decode(eventid), 'utf-8')

        event = calendar.event_by_url(url)

        data = utils.convert_event(event)

        resp.content_type = 'application/json'
        resp.body = json.dumps(data, indent=2)  # TODO stream
