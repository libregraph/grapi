"""Batch request schema."""
import jsonschema

from grapi.api.v1.config import PREFIX

schema = {
    "type": "object",
    "properties": {
        "requests": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[1-9][0-9]*$",
                    },
                    "method": {
                        "type": "string",
                        "enum": [
                            "GET",
                            "POST",
                            "PUT",
                            "PATCH",
                            "DELETE",
                        ],
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
                            "type": "string",
                        },
                    },
                    "dependsOn": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {
                            "type": "string"
                        },
                    }
                },
                "required": [
                    "id",
                    "method",
                    "url",
                ],
                "additionalProperties": False,
            }
        }
    },
    "required": [
        "requests"
    ],
}

schema_validator = jsonschema.Draft4Validator(schema)
