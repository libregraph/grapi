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

# getSchedule
_getschedule_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "availabilityViewInterval": {"type": "number", "minimum": 5, "maximum": 1440},
        "startTime": _dateTimeTimeZone,
        "endTime": _dateTimeTimeZone,
        "schedules": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["startTime", "endTime", "schedules"]
}

# attachments
_base_attachment_schema_fields = {
    "@odata.type": {
      "type": "string",
      "enum": [
          "#microsoft.graph.fileAttachment",
          "#microsoft.graph.itemAttachment",
          "#microsoft.graph.referenceAttachment",
      ],
    },
    "contentType": {
        "type": "string",
    },
    "id": {
        "type": "string",
    },
    "isInline": {
        "type": "boolean",
    },
    "lastModifiedDateTime": {
        "type": "string",
        "format": "date-time",
    },
    "name": {
        "type": "string",
    },
    "size": {
        "type": "integer",
    },
}

_file_attachment_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        **_base_attachment_schema_fields,
        "contentLocation": {
            "type": "string",
        },
        "contentId": {
            "type": "string",
        },
        "contentBytes": {
            "type": "string",
        },
        "required": [
            "@odata.type",
            "name",
            "contentBytes",
        ],
        "additionalProperties": False,
    }
}

_item_attachment_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        **_base_attachment_schema_fields,
        "item": {
            "type": "object",
            "properties": {
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "minItems": 1,
                },
                "changeKey": {
                    "type": "string",
                },
                "createdDateTime": {
                    "type": "string",
                    "format": "date-time",
                },
                "id": {
                    "type": "string",
                },
                "lastModifiedDateTime": {
                    "type": "string",
                    "format": "date-time",
                }
            },
            "required": [
                "categories",
            ],
            "additionalProperties": False,
        },
        "required": [
            "@odata.type",
            "name",
            "item",
        ],
        "additionalProperties": False,
    }
}

_reference_attachment_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        **_base_attachment_schema_fields,
        "required": [
            "@odata.type",
            "name",
        ],
        "additionalProperties": False
    }
}

# message
_message_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "definitions": {
        "itemBody": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                },
                "contentType": {
                    "type": "string",
                }
            },
            "required": [
                "content",
                "contentType"
            ],
            "additionalProperties": False
        },
        "recipient": {
            "type": "object",
            "properties": {
                "emailAddress": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1
                        },
                        "address": {
                            "type": "string",
                            "format": "email"
                        }
                    },
                    "required": [
                        "name",
                        "address"
                    ],
                    "additionalProperties": False
                }
            },
            "required": [
                "emailAddress"
            ],
            "additionalProperties": False
        },
        "recipients": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "$ref": "#/definitions/recipient"
            }
        },
        "optionalRecipients": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "$ref": "#/definitions/recipient"
            }
        },
    },
    "properties": {
        "bccRecipients": {
            "$ref": "#/definitions/optionalRecipients",
        },
        "body": {
            "$ref": "#/definitions/itemBody"
        },
        "bodyPreview": {
            "type": "string",
            "maxLength": 255
        },
        "categories": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string"
            }
        },
        "ccRecipients": {
            "$ref": "#/definitions/optionalRecipients",
        },
        "changeKey": {
            "type": "string"
        },
        "conversationId": {
            "type": ["string", "null"]
        },
        "conversationIndex": {
            "type": "string"
        },
        "createdDateTime": {
            "type": "string",
            "format": "date-time"
        },
        "flag": {
            "type": "object",
            "properties": {
                "completedDateTime": {
                    "type": "string",
                    "format": "date-time"
                },
                "dueDateTime": {
                    "type": "string",
                    "format": "date-time"
                },
                "flagStatus": {
                    "type": "string",
                    "enum": ["notFlagged", "complete", "flagged"]
                },
                "startDateTime": {
                    "type": "string",
                    "format": "date-time"
                }
            },
            "dependencies": {
                "dueDateTime": ["startDateTime"]
            },
            "additionalProperties": False
        },
        "from": {
            "$ref": "#/definitions/recipient"
        },
        "hasAttachments": {
            "type": "boolean"
        },
        "id": {
            "type": "string"
        },
        "importance": {
            "type": "string",
            "enum": ["Low", "Normal", "High"]
        },
        "inferenceClassification": {
            "type": "string",
            "enum": ["focused", "other"]
        },
        "internetMessageHeaders": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1
                },
                "value": {
                    "type": "string"
                }
            },
            "required": [
                "name",
                "address"
            ],
            "additionalProperties": False
        },
        "internetMessageId": {
            "type": "string"
        },
        "isDeliveryReceiptRequested": {
            "type": "boolean"
        },
        "isDraft": {
            "type": "boolean"
        },
        "isRead": {
            "type": "boolean"
        },
        "isReadReceiptRequested": {
            "type": "boolean"
        },
        "lastModifiedDateTime": {
            "type": "string",
            "format": "date-time"
        },
        "parentFolderId": {
            "type": "string",
            "minLength": 1
        },
        "receivedDateTime": {
            "type": "string",
            "format": "date-time"
        },
        "replyTo": {
            "$ref": "#/definitions/optionalRecipients",
        },
        "sender": {
            "$ref": "#/definitions/recipient"
        },
        "sentDateTime": {
            "type": "string",
            "format": "date-time"
        },
        "subject": {
            "type": "string",
        },
        "toRecipients": {
            "$ref": "#/definitions/recipients",
        },
        "uniqueBody": {
            "$ref": "#/definitions/itemBody"
        },
        "webLink": {
            "type": "string"
        },
        "extensions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    }
                },
                "required": [
                    "id"
                ],
                "additionalProperties": False
            }
        },
        "multiValueExtendedProperties": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "value": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "id",
                    "value"
                ],
                "additionalProperties": False
            }
        },
        "singleValueExtendedProperties": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string"
                    },
                    "value": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "id",
                    "value"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": ["toRecipients", "subject", "body"],
    "additionalProperties": False
}

_folder_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "displayName": {
            "type": "string",
            "minLength": 1
        },
    },
    "required": ["displayName"]
}

_destination_id_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "destinationId": {
            "type": "string",
            "minLength": 1
        }
    },
    "required": ["destinationId"]
}

event_schema = jsonschema.Draft4Validator(_event_schema)
mr_schema = jsonschema.Draft4Validator(_mr_schema)
get_schedule_schema = jsonschema.Draft4Validator(_getschedule_schema)
file_attachment_schema = jsonschema.Draft4Validator(_file_attachment_schema)
item_attachment_schema = jsonschema.Draft4Validator(_item_attachment_schema)
reference_attachment_schema = jsonschema.Draft4Validator(_reference_attachment_schema)
message_schema = jsonschema.Draft4Validator(_message_schema)
folder_schema = jsonschema.Draft4Validator(_folder_schema)
destination_id_schema = jsonschema.Draft4Validator(_destination_id_schema)
