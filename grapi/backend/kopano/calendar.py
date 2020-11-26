# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from kopano.errors import NotFoundError

from .event import EventResource
from .folder import FolderResource
from .resource import _dumpb_json, _start_end, _tzdate, parse_datetime_timezone
from .schema import event_schema, get_schedule_schema
from .utils import HTTPBadRequest, _folder, _server_store, experimental


def get_fbinfo(req, block):
    return {
        'status': block.status,
        'start': _tzdate(block.start, None, req),
        'end': _tzdate(block.end, None, req)
    }


class CalendarResource(FolderResource):
    fields = FolderResource.fields.copy()
    fields.update({
        'name': lambda folder: folder.name,
    })

    def handle_get_calendarView(self, req, resp, folder):
        start, end = _start_end(req)

        def yielder(**kwargs):
            for occ in folder.occurrences(start, end, **kwargs):
                yield occ
        data = self.generator(req, yielder)
        fields = EventResource.fields
        self.respond(req, resp, data, fields)

    def handle_get_events(self, req, resp, folder):
        data = self.generator(req, folder.items, folder.count)
        fields = EventResource.fields
        self.respond(req, resp, data, fields)

    def handle_get(self, req, resp, folder):
        data = folder
        fields = None

        self.respond(req, resp, data, fields)

    def on_get(self, req, resp, userid=None, folderid=None, method=None):
        handler = None

        if method == 'calendarView':
            handler = self.handle_get_calendarView

        elif method == 'events':
            handler = self.handle_get_events

        elif method:
            raise HTTPBadRequest("Unsupported calendar segment '%s'" % method)

        else:
            handler = self.handle_get

        server, store, userid = req.context.server_store
        folder = _folder(store, folderid or 'calendar')
        handler(req, resp, folder=folder)

    def handle_post_events(self, req, resp, folder):
        fields = self.load_json(req)
        self.validate_json(event_schema, fields)

        item = self.create_message(folder, fields, EventResource.set_fields)
        if fields.get('attendees', None):
            # NOTE(longsleep): Sending can fail with NO_ACCCESS if no permission to outbox.
            item.send()
        self.respond(req, resp, item, EventResource.fields)

    @experimental
    def handle_post_schedule(self, req, resp, folder):
        fields = self.load_json(req)
        self.validate_json(get_schedule_schema, fields)

        freebusytimes = []

        server, store, userid = _server_store(req, None, self.options)

        email_addresses = fields['schedules']
        start = parse_datetime_timezone(fields['startTime'], 'startTime')
        end = parse_datetime_timezone(fields['endTime'], 'endTime')
        # TODO: implement availabilityView https://docs.microsoft.com/en-us/graph/outlook-get-free-busy-schedule
        availability_view_interval = fields.get('availabilityViewInterval', 60)

        for address in email_addresses:
            try:
                user = server.user(email=address)
            except NotFoundError:
                continue  # TODO: silent ignore or raise exception?

            fbdata = {
                'scheduleId': address,
                'availabilityView': '',
                'scheduleItems': [],
                'workingHours': {},
            }

            try:
                blocks = user.freebusy.blocks(start=start, end=end)
            except NotFoundError:
                logging.warning('no public store available, unable to retrieve freebusy data')
                continue

            if not blocks:
                continue

            fbdata['scheduleItems'] = [get_fbinfo(req, block) for block in blocks]
            freebusytimes.append(fbdata)

        data = {
            "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#Collection(microsoft.graph.scheduleInformation)",
            "value": freebusytimes,
        }
        resp.content_type = 'application/json'
        resp.body = _dumpb_json(data)

    def on_post(self, req, resp, userid=None, folderid=None, method=None):
        handler = None

        if method == 'events':
            handler = self.handle_post_events

        elif method == 'getSchedule':
            handler = self.handle_post_schedule

        elif method:
            raise HTTPBadRequest("Unsupported calendar segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in calendar")

        server, store, userid = req.context.server_store
        folder = _folder(store, folderid or 'calendar')
        handler(req, resp, folder=folder)
