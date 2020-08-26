# SPDX-License-Identifier: AGPL-3.0-or-later

from . import Resource, utils


class UserResource(Resource):

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None, method=None):
        if method == 'messages':  # TODO store-wide?
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
            # TODO: hardcoded api prefix
            data = {
                '@odata.context': '/api/gc/v1/me/messages',
                '@odata.nextLink': '/api/gc/v1/me/messages?$skip=10',
                'value': value,
            }
        self.respond_json(req, data)
