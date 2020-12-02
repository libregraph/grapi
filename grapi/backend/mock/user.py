from grapi.backend.mock import Resource

from .data import USERS


class UserResource(Resource):
    def __init__(self, options):
        Resource.__init__(self, options)

    def on_get(self, req, resp, userid=None, folderid=None, itemid=None):
        data = {
            '@odata.context': '/api/gc/v1/users',
            'value': USERS,
        }

        self.respond_json(resp, data)
