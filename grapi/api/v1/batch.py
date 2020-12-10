# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Implementation of /$batch call documented
# https://docs.microsoft.com/en-us/graph/json-batching?context=graph%2Fapi%2F1.0&view=graph-rest-1.0#response-format

import logging

from falcon.testing import TestClient

from grapi.api.v1.decorators import experimental
from grapi.api.v1.graph import AdjacencyMatrix as Graph
from grapi.api.v1.resource import HTTPBadRequest, Resource
from grapi.api.v1.schema.batch import schema_validator

GOOD_STATUS_CODES = (200, 201, 204)


def process_request(data):
    """Convert request to graph and dict.

    Args:
        data (dict): request payload.

    Returns:
        Tuple[AdjacencyMatrix,Dict]: generated graph and requests data map based on data.
    """
    requests = {}
    graph = Graph(len(data['requests']))

    for request in data["requests"]:

        # Graph index starts from 0, but requests start start from 1.
        # So, here we deduct it by 1 to make it compatible with Graph indices.
        request_id = int(request["id"]) - 1

        if request_id in requests:
            raise ValueError("duplicate request ID")

        if request_id > graph.num_vertices:
            raise ValueError("request ID is outbound")

        # Prepare request data map to speed up our access to O(1)
        requests.update({
            request_id: {
                "request": request,
                "processed": False,
            },
        })

        # Connect IDs and depends IDs
        if request.get("dependsOn"):
            for depends_id in request["dependsOn"]:
                # Deducting by 1 is because Graph index starts from 0.
                # So, we need to make request IDs compatible with Graph indices.
                graph.add_edge(int(depends_id) - 1, request_id)

    return graph, requests


def fail_dependent_requests(graph, request_id, requests):
    """Mark all dependent requests as failed.

    Args:
        graph (AdjacencyMatrix): graph instance.
        request_id (int): request ID.
        requests (dict): requests data map (result of process_request).

    Returns:
        list: list of prepared responses for user.
    """
    responses = []
    requests_chain = graph.get_vertices_chain(request_id)
    for depend_request_id, chained_request_ids in requests_chain.items():

        # Increasing by 1 is necessary to make Graph indices
        # compatible with request IDs.
        depend_request_id += 1

        for chained_request_id in chained_request_ids:
            requests[chained_request_id]["processed"] = True

            # Increasing by 1 is necessary to make Graph indices
            # compatible with request IDs.
            chained_real_request_id = chained_request_id + 1

            # Generate response for this request.
            responses.append({
                "status": 424,
                "id": str(chained_real_request_id),
                "body": {
                    "error": {
                        "code": 424,
                        "message": "failed dependency - ID: {}".format(depend_request_id),
                    },
                },
                "headers": {
                    "content-type": "application/json"
                },
            })

    return responses


@experimental
class BatchResource(Resource):
    def __init__(self, options, api):
        super().__init__(options)
        self.api = api

    def on_post(self, req, resp):
        data = self.load_json(req)
        self.validate_json(schema_validator, data)

        # Processing on requests to generate graph and data map.
        try:
            graph, requests = process_request(data)
            requests_order = graph.get_sorted_vertices()
        except ValueError as e:
            msg = str(e).replace("graph", "request")
            raise HTTPBadRequest(msg)

        responses = []
        client = TestClient(self.api)

        for request_id in requests_order:
            request = requests[request_id]["request"]
            # Ignore a request which is already processed.
            # It is used for dependency failure.
            if requests[request_id]["processed"]:
                continue
            requests[request_id]["processed"] = True

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

                # Mark all dependent requests as failed.
                responses.extend(
                    fail_dependent_requests(graph, request_id, requests)
                )

            else:
                if result.status_code == 200:
                    headers = result.headers
                    response['headers'] = {'content-type': 'application/json'}

                    if headers.get('content-type') == 'application/json':
                        response['body'] = result.json
                    else:
                        message = 'content-type: {} is unsupported.'.format(headers.get('content-type'))
                        response['status'] = 400
                        response['body'] = {'error': {'code': 400, 'message': message}}

                        # Mark all dependent requests as failed.
                        responses.extend(
                            fail_dependent_requests(graph, request_id, requests)
                        )

                # if an unexpected status code is returned set the error object
                if result.status_code not in GOOD_STATUS_CODES:
                    response['body'] = {'error': {
                                        'code': result.status_code,
                                        'message': result.status,
                                        'headers': {'content-type': 'application/json'}
                                        }}

                response['status'] = result.status_code
                responses.append(response)

        self.respond_json(resp, responses)
