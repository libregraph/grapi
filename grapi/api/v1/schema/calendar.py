"""Calendar JSON schema."""
import jsonschema

# get schedule
_get_schedule_schema = {
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
    },
    "properties": {
        "availabilityViewInterval": {
            "type": "integer",
            "minimum": 5,
            "maximum": 1440,
        },
        "startTime": {
            "$ref": "#/definitions/date_time_timezone",
        },
        "endTime": {
            "$ref": "#/definitions/date_time_timezone",
        },
        "schedules": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "startTime",
        "endTime",
        "schedules",
    ],
}

get_schedule_schema_validator = jsonschema.Draft4Validator(_get_schedule_schema)
