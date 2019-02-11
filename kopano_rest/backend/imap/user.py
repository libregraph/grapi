# SPDX-License-Identifier: AGPL-3.0-or-later

import json

from .resource import Resource
from . import utils

class UserResource(Resource):

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        if method == 'messages': # TODO store-wide?
            M = utils.login()
            M.select()
            typ, data = M.search(None, 'ALL')
            count = 0
            value = []
            for num in data[0].split():
                typ, data = M.fetch(num, '(RFC822)')
                value.append(utils.convert_message(num, data))
                count += 1
                if count >= 10:
                    break
            utils.logoff(M)
            data = {
                '@odata.context': '/api/gc/v1/me/messages',
                '@odata.nextLink': '/api/gc/v1/me/messages?$skip=10',
                'value': value,
            }

        resp.content_type = 'application/json'
        resp.body = json.dumps(data, indent=2) # TODO stream
