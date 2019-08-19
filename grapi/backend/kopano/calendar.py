# SPDX-License-Identifier: AGPL-3.0-or-later

from .utils import (
    _server_store, _folder, HTTPBadRequest, experimental
)
from .folder import (
    FolderResource
)
from .event import (
    EventResource
)
from .resource import (
    _start_end
)


@experimental
class CalendarResource(FolderResource):
    fields = FolderResource.fields.copy()
    fields.update({
        'displayName': lambda folder: folder.name,
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

        server, store, userid = _server_store(req, userid, self.options)
        folder = _folder(store, folderid or 'calendar')
        handler(req, resp, folder=folder)

    def handle_post_events(self, req, resp, folder):
        fields = self.load_json(req)

        item = self.create_message(folder, fields, EventResource.set_fields)
        if fields.get('attendees', None):
            # NOTE(longsleep): Sending can fail with NO_ACCCESS if no permission to outbox.
            item.send()
        self.respond(req, resp, item, EventResource.fields)

    def on_post(self, req, resp, userid=None, folderid=None, method=None):
        handler = None

        if method == 'events':
            handler = self.handle_post_events

        elif method:
            raise HTTPBadRequest("Unsupported calendar segment '%s'" % method)

        else:
            raise HTTPBadRequest("Unsupported in calendar")

        server, store, userid = _server_store(req, userid, self.options)
        folder = store.calendar  # TODO
        handler(req, resp, folder=folder)
