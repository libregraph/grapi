# SPDX-License-Identifier: AGPL-3.0-or-later
import datetime

from .resource import Resource, _start_end, _tzdate
from .utils import experimental


class ReminderResource(Resource):
    fields = {
        'eventId': lambda occ: occ.eventid,
        'changeKey': lambda occ: occ.item.changekey,
        'eventSubject': lambda occ: occ.subject,
        'eventStartTime': lambda req, occ: _tzdate(occ.start, occ.tzinfo, req),
        'eventEndTime': lambda req, occ: _tzdate(occ.end, occ.tzinfo, req),
        'eventLocation': lambda occ: occ.location,
        'reminderFireTime': lambda req, occ: _tzdate(occ.start - datetime.timedelta(minutes=occ.reminder_minutes), occ.tzinfo, req),
    }

    @experimental
    def on_get_reminder_view(self, req, resp):
        # TODO use restriction in pyko: calendar.reminders(start, end)?
        start, end = _start_end(req)

        store = req.context.server_store[1]

        def yielder(**kwargs):
            for occ in store.calendar.occurrences(start, end):
                if occ.reminder:
                    yield occ
        data = self.generator(req, yielder)
        self.respond(req, resp, data, ReminderResource.fields)
