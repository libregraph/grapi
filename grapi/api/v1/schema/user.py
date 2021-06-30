"""User JSON schema."""
import jsonschema

from .message import _create_schema

_sendmail_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "definitions": {
        **_create_schema['definitions'],
    },
    "properties": {
        "message": {
            "type": "object",
            "properties": {
                **_create_schema['properties'],
            }
        },
        "saveToSentItems": {
            "type": "boolean",
        },
    },
    "required": [
        "message",
    ],
}

sendmail_schema_validator = jsonschema.Draft4Validator(_sendmail_schema)
