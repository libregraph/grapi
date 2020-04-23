import jsonschema

# dateTimmeTimeZone resource type
_dateTimeTimeZone = {
    "type": "object",
    "properties": {
        "DateTime": {"type": "string"},
        "TimeZone": {"type": "string"},
    },
}

# https://developer.microsoft.com/en-us/graph/docs/api-reference/v1.0/resources/event
# event resource type
_event_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "body": {
            "content": "string",
            "contentType": "string"
        },
        "start": _dateTimeTimeZone,
        "end": _dateTimeTimeZone,
        "isAllDay": {"type": "boolean"},
        "sensitivity": {
            "type": "string",
            "enum": ["normal", "personal", "private", "confidential"]
        },
        "showAs": {
            "enum": ["free", "tentative", "busy", "oof", "workingElsewhere", "unknown"]
        },
    },
    "required": ["subject", "start", "end"],
}

# meeting request accept/tentativelyAccept/decline
_mr_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "comment": {"type": "string"},
        "sendResponse": {"type": "boolean"},
    },
}


# POST subscriptions
_subscription_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "clientState": {"type": "string"},
        "expirationDateTime": {"type": "string"},
        "resource": {"type": "string"},
        "notificationUrl": {"type:": "string"},
        "changeType": {"type": "string"},
    },
    "required": ["expirationDateTime", "notificationUrl", "resource", "changeType"],
}


# PATCH subscriptions
_update_subscription_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "expirationDateTime": {"type": "string"},
    },
    "required": ["expirationDateTime"],
}

event_schema = jsonschema.Draft4Validator(_event_schema)
subscription_schema = jsonschema.Draft4Validator(_subscription_schema)
update_subscription_schema = jsonschema.Draft4Validator(_update_subscription_schema)
mr_schema = jsonschema.Draft4Validator(_mr_schema)
