"""Apply request ID to the context."""
import uuid


class RequestId:
    """Add request ID in the request's context."""

    def process_request(self, req, resp):
        """Built-in Falcon method for middleware.

        Args:
            req (Request): Falcon request object.
            resp (Response): Falcon response object.
        """
        req.context.request_id = str(uuid.uuid4())
