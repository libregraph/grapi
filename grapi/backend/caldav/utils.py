# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import codecs
import os

import caldav
import vobject

HOST = os.getenv('CALDAV_SERVER')
USER = os.getenv('GRAPI_USER')
PASSWORD = os.getenv('GRAPI_PASSWORD')

def calendar():
    client = caldav.DAVClient(HOST, username=USER, password=PASSWORD)
    principal = client.principal()
    for calendar in principal.calendars():
        if calendar.name == 'Calendar':  # TODO better lookup
            return calendar

def convert_event(event):
    vobj = vobject.readOne(event.data)
    fmt = '%Y-%m-%dT%H:%M:%S'
    return {
        'id': codecs.decode(base64.urlsafe_b64encode(codecs.encode(str(event.url), 'utf-8')), 'ascii'),  # TODO don't use full url..
        'subject': vobj.vevent.summary.value,
        'start': {
            'timeZone': 'UTC',  # TODO
            'dateTime': vobj.vevent.dtstart.value.strftime(fmt),
        },
        'end': {
            'timeZone': 'UTC',  # TODO
            'dateTime': vobj.vevent.dtend.value.strftime(fmt),
        },
    }
