"""Subscription data schema."""
import jsonschema

# POST subscriptions
create_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "changeType": {
            "type": "string",
            # "pattern": "(created|updated|deleted){1}(?:(?=,)(created|updated|deleted))*"
        },
        "notificationUrl": {
            "type:": "string",
            "pattern": "http(s)?://\\w+",
        },
        "lifecycleNotificationUrl": {
            "type": "string",
            "pattern": "http(s)?://\\w+",
        },
        "resource": {
            "type": "string",
        },
        "expirationDateTime": {
            "type": "string",
            "format": "date-time",
        },
        "clientState": {
            "type": "string",
            "maxLength": 128,
        },
        "includeResourceData": {
            "type": "boolean",
            "default": False,
        },
        "encryptionCertificate": {
            "type": "string",
        },
        "encryptionCertificateId": {
            "type": "string",
        },
        "latestSupportedTlsVersion": {
            "type": "string",
            "enum": [
                "v1_0",
                "v1_1",
                "v1_2",
                "v1_3",
            ]
        }
    },
    "additionalProperties": False,
    "required": [
        "changeType",
        "notificationUrl",
        "resource",
        "expirationDateTime",
    ],
}

# PATCH subscriptions
update_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "expirationDateTime": {
            "type": "string",
            "format": "date-time",
        },
    },
    "required": [
        "expirationDateTime"
    ],
}

create_schema_validator = jsonschema.Draft4Validator(create_schema)
update_schema_validator = jsonschema.Draft4Validator(update_schema)
