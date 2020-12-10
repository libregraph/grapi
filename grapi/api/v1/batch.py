"""Batch request handler."""
# SPDX-License-Identifier: AGPL-3.0-or-later
from urllib.parse import urlparse

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


def generate_response(status_code, request_id, response=None, message=None):
    """Generate response body.

    Args:
        status_code (int): HTTP status code of the received response.
        request_id (str): request ID.
        response (Result): Falcon processed response object. Defaults to None.
        message (str): customized message. Defaults to None.

    Returns:
        Dict: generated response data.
    """
    if status_code not in GOOD_STATUS_CODES:
        body = {
            "error": {
                "code": status_code,
                "message": message or response.status,
            },
        }
    else:
        body = response.json if status_code != 204 else None

    return {
        "id": request_id,
        "status": status_code,
        "body": body,
        "headers": {
            "content-type": "application/json"
        },
    }


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
            responses.append(
                generate_response(
                    424,
                    str(chained_real_request_id),
                    message="Failed dependency - ID: {}".format(depend_request_id)
                )
            )

    return responses


@experimental
class BatchResource(Resource):
    """Batch resource implementation."""

    def __init__(self, options, api):
        super().__init__(options)
        self.api = api

    def on_post(self, req, resp):
        """Handle POST request.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        data = self.load_json(req)
        self.validate_json(schema_validator, data)

        # Processing on requests to generate graph and data map.
        try:
            graph, requests = process_request(data)
            requests_order = graph.get_sorted_vertices()
        except ValueError as e:
            # Change context by replacing graph-related words to request-related words.
            msg = str(e).replace("graph", "request").replace("vertex", "request")
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

            # Headers.
            custom_headers = request.get("headers", {})
            # dict merging has right-to-left priority
            headers = {**custom_headers, **req.headers}

            # URL and query string.
            parsed_url = urlparse(request.get("url", ""))

            try:
                response = client.simulate_request(
                    method=request["method"],
                    path=parsed_url.path,
                    headers=headers,
                    query_string=parsed_url.query,
                    json=request.get("body", {})
                )
            except AssertionError:
                responses.append(generate_response(404, request["id"], message="Not found."))

                # Mark all dependent (chained) requests as failed.
                responses.extend(
                    fail_dependent_requests(graph, request_id, requests)
                )

            else:
                if response.status_code in GOOD_STATUS_CODES:
                    responses.append(
                        generate_response(response.status_code, request["id"], response)
                    )
                else:
                    if "application/json" in response.headers.get("content-type", ""):
                        responses.append(
                            generate_response(response.status_code, request["id"], response)
                        )
                    else:
                        responses.append(
                            generate_response(
                                400, request["id"], response, "Unsupported content-type."
                            )
                        )

                    # Mark all dependent requests as failed.
                    responses.extend(
                        fail_dependent_requests(graph, request_id, requests)
                    )

        self.respond_json(resp, responses)
