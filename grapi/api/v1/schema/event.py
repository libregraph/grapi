"""Event JSON schema."""
import jsonschema

# create event resource type
_create_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "definitions": {
        "date_time_timezone": {
            "type": "object",
            "properties": {
                "DateTime": {
                    "type": "string",
                },
                "TimeZone": {
                    "type": "string",
                },
            },
        },
        "physical_address": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                },
                "countryOrRegion": {
                    "type": "string",
                },
                "postalCode": {
                    "type": "string",
                },
                "state": {
                    "type": "string",
                },
                "street": {
                    "type": "string",
                },
            },
        },
        "coordinates": {
            "type": "object",
            "properties": {
                "accuracy": {
                    "type": "number",
                },
                "altitude": {
                    "type": "number",
                },
                "altitudeAccuracy": {
                    "type": "number",
                },
                "latitude": {
                    "type": "number",
                },
                "longitude": {
                    "type": "number",
                },
            }
        }
    },
    "properties": {
        "subject": {
            "type": "string",
        },
        "body": {
            "content": "string",
            "contentType": "string",
        },
        "start": {
            "$ref": "#/definitions/date_time_timezone",
        },
        "end": {
            "$ref": "#/definitions/date_time_timezone",
        },
        "isAllDay": {
            "type": "boolean",
        },
        "sensitivity": {
            "type": "string",
            "enum": [
                "normal",
                "personal",
                "private",
                "confidential",
            ],
        },
        "showAs": {
            "enum": [
                "free",
                "tentative",
                "busy",
                "oof",
                "workingElsewhere",
                "unknown",
            ],
        },
        "categories": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string"
            },
        },
        "location": {
            "type": "object",
            "properties": {
                "address": {
                    "$ref": "#/definitions/physical_address",
                },
                "coordinates": {
                    "$ref": "#/definitions/coordinates",
                },
                "displayName": {
                    "type": "string"
                },
                "locationEmailAddress": {
                    "type": "string"
                },
                "locationUri": {
                    "type": "string"
                },
                "locationType": {
                    "type": "string"
                },
                "uniqueId": {
                    "type": "string"
                },
                "uniqueIdType": {
                    "type": "string"
                },
            },
        },
    },
    "required": [
        "subject",
        "start",
        "end",
    ],
}

# meeting request accept/tentativelyAccept/decline
_action_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "comment": {
            "type": "string"
        },
        "proposedNewTime": {
            "type": "object",
            "properties": {
                "start": {
                    "type": "object",
                    "properties": {
                        "dateTime": {
                            "type": "string",
                            "format": "date-time"
                        },
                        "timeZone": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dateTime",
                        "timeZone"
                    ]
                },
                "end": {
                    "type": "object",
                    "properties": {
                        "dateTime": {
                            "type": "string",
                            "format": "date-time"
                        },
                        "timeZone": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "dateTime",
                        "timeZone"
                    ]
                }
            },
            "required": [
                "start",
                "end"
            ]
        },
        "sendResponse": {
            "type": "boolean"
        }
    }
}

create_schema_validator = jsonschema.Draft4Validator(_create_schema)
action_schema_validator = jsonschema.Draft4Validator(_action_schema)
