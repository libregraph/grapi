# SPDX-License-Identifier: AGPL-3.0-or-later

import datetime
import json

from . import utils, Resource

class UserResource(Resource):

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        if method == 'events': # TODO store-wide?
            value = []

            calendar = utils.calendar()
            for event in calendar.date_search(datetime.datetime(2019, 1, 1), datetime.datetime(2020, 1, 1)):
                value.append(utils.convert_event(event))

            data = {'value': value}

            resp.content_type = 'application/json'
            resp.body = json.dumps(data, indent=2) # TODO stream
