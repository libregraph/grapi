"""Loading and validating a request body."""
import re

from grapi.api.v1.api_resource import APIResource
from grapi.api.v1.config import PREFIX
from grapi.api.v1.resource import HTTPBadRequest, Resource


class RequestBodyExtractor:
    """Request body extractor middleware."""

    _methods_schema = {"POST", "PUT", "PATCH"}

    def __init__(self):
        self._prefix_length = len(PREFIX)
        self._placeholder_pattern = re.compile("[{}]")

    def _get_method_name(self, req):
        """Geet method name based on URI.

        Args:
            req (Request): Falcon request object.

        Returns:
            str: method name of the destination resource which will be called.
        """
        clean_uri = req.uri_template[self._prefix_length:].replace("/", "_")
        clean_uri = self._placeholder_pattern.sub("", clean_uri)
        return "on_{}{}".format(req.method.lower(), clean_uri)

    def process_request(self, req, resp):
        """Built-in Falcon method for middleware."""
        if req.method not in self._methods_schema:
            return

        try:
            req.context.json_data = Resource.load_json(req)
        except HTTPBadRequest:
            resp.complete = True
            raise

    def process_resource(self, req, resp, resource, params):
        """Built-in Falcon method for middleware."""
        if not isinstance(resource, APIResource):
            return

        if req.method not in self._methods_schema:
            return

        actual_resource = resource.getResource(req)

        # Schema validation.
        schema = getattr(actual_resource, "{}_schema".format(self._get_method_name(req)), None)
        if schema:
            try:
                actual_resource.validate_json(schema, req.context.json_data)
            except HTTPBadRequest:
                resp.complete = True
                raise
