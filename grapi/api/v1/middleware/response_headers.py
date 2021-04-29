"""Response headers middleware."""
import falcon


class ResponseHeaders:
    """Update response headers."""

    def process_response(self, req, resp, resource, req_succeeded):
        """Built-in Falcon middleware method."""
        if resp.status == falcon.HTTP_204 or resp.status == falcon.HTTP_404:
            return

        if not resp.content_type:
            resp.content_type = "application/json"
