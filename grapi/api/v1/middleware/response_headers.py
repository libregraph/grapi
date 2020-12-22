"""Response headers middleware."""
import falcon


class ResponseHeaders:
    """Update response headers."""

    def process_response(self, req, resp, resource, req_succeeded):
        """Built-in Falcon middleware method."""
        if resp.status == falcon.HTTP_204:
            return

        resp.content_type = "application/json"
