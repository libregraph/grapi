from grapi.backend.mock import Resource

from .data import MESSAGES


class MessageResource(Resource):
    def __init__(self, options):
        Resource.__init__(self, options)

    def on_get_messages(self, req, resp):
        data = {
            '@odata.context': '/api/gc/v1/me/messages',
            '@odata.nextLink': '/api/gc/v1/me/messages?$skip=10',
            'value': MESSAGES,
        }

        self.respond_json(resp, data)
