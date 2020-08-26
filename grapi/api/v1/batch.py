# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Implementation of /$batch call documented
# https://docs.microsoft.com/en-us/graph/json-batching?context=graph%2Fapi%2F1.0&view=graph-rest-1.0#response-format

import json  # TODO(jelle): refactor grapi and use ujson
import logging

import falcon
import jsonschema
from falcon.testing import TestClient

from grapi.api.v1.config import PREFIX
from grapi.api.v1.decorators import experimental
from grapi.api.v1.resource import Resource

GOOD_STATUS_CODES = (200, 204)


_batchRequest = {
    "type": "object",
    "properties": {
        "requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[1-9][0-9]*$",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "DELETE"],
                    },
                    "url": {
                        "type": "string",
                        "pattern": "^{}".format(PREFIX),
                    },
                    "body": {
                        "type": "object",
                    },
                    "headers": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string"
                        }
                    },
                    "dependsOn": {
                        "type": "array",
                    }
                },
                "required": ["id", "method", "url"],
            }
        }
    },
    "required": ["requests"],
}

batch_schema = jsonschema.Draft4Validator(_batchRequest)


@experimental
class BatchResource(Resource):
    def __init__(self, options, api):
        super().__init__(options)
        self.api = api

    # TODO(jelle): implement dependsOn
    def on_post(self, req, resp):
        data = self.load_json(req)
        self.validate_json(batch_schema, data)
        responses = []
        client = TestClient(self.api)

        for request in data['requests']:
            response = {'id': request['id'], 'body': 'null'}
            custom_headers = request.get('headers', {})
            # dict merging has right-to-left priority
            headers = {**custom_headers, **req.headers}

            try:
                # TODO(jelle): implement POST/PATCH/PUT submission
                result = client.simulate_request(method=request['method'], path=request['url'], headers=headers)
            except AssertionError as exc:  # request might have failed with no content-type
                logging.exception(exc)
                response['status'] = 500
                response['body'] = {'error': {'code': 500, 'message': 'An error occurred executing the request.'}}
                response['headers'] = {'content-type': 'application/json'}
                responses.append(response)
                continue

            if result.status_code == 200:
                headers = result.headers
                response['headers'] = {'content-type': 'application/json'}

                if headers.get('content-type') == 'application/json':
                    response['body'] = result.json
                else:
                    message = 'content-type: {} is unsupported.'.format(headers.get('content-type'))
                    response['status'] = 400
                    response['body'] = {'error': {'code': 400, 'message': message}}

            # if an unexpected status code is returned set the error object
            if result.status_code not in GOOD_STATUS_CODES:
                response['body'] = {'error': {
                                    'code': result.status_code,
                                    'message': result.status,
                                    'headers': {'content-type': 'application/json'}
                                    }}

            response['status'] = result.status_code
            responses.append(response)

        resp.content_type = 'application/json'
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(responses, indent=2)  # TODO(jelle): stream
