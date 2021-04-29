"""Message JSON schema."""
import jsonschema

# Message schema (add).
_create_schema = {
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

# Message schema (update).
_update_schema = {
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
                },
            },
            "additionalProperties": False,
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
                            "format": "email",
                        },
                    },
                    "additionalProperties": False,
                }
            },
            "additionalProperties": False,
        },
        "recipients": {
            "type": "array",
            "minItems": 1,
            "uniqueItems": True,
            "items": {
                "$ref": "#/definitions/recipient",
            },
        },
        "optionalRecipients": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "$ref": "#/definitions/recipient",
            },
        },
    },
    "properties": {
        "bccRecipients": {
            "$ref": "#/definitions/optionalRecipients",
        },
        "body": {
            "$ref": "#/definitions/itemBody",
        },
        "bodyPreview": {
            "type": "string",
            "maxLength": 255,
        },
        "categories": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string",
            },
        },
        "ccRecipients": {
            "$ref": "#/definitions/optionalRecipients",
        },
        "changeKey": {
            "type": "string",
        },
        "conversationId": {
            "type": ["string", "null"],
        },
        "conversationIndex": {
            "type": "string",
        },
        "createdDateTime": {
            "type": "string",
            "format": "date-time",
        },
        "flag": {
            "type": "object",
            "properties": {
                "completedDateTime": {
                    "type": "string",
                    "format": "date-time",
                },
                "dueDateTime": {
                    "type": "string",
                    "format": "date-time",
                },
                "flagStatus": {
                    "type": "string",
                    "enum": ["notFlagged", "complete", "flagged"],
                },
                "startDateTime": {
                    "type": "string",
                    "format": "date-time",
                },
            },
            "dependencies": {
                "dueDateTime": ["startDateTime"]
            },
            "additionalProperties": False,
        },
        "from": {
            "$ref": "#/definitions/recipient",
        },
        "hasAttachments": {
            "type": "boolean",
        },
        "id": {
            "type": "string",
        },
        "importance": {
            "type": "string",
            "enum": ["Low", "Normal", "High"],
        },
        "inferenceClassification": {
            "type": "string",
            "enum": ["focused", "other"],
        },
        "internetMessageHeaders": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 1,
                },
                "value": {
                    "type": "string",
                },
            },
            "additionalProperties": False,
        },
        "internetMessageId": {
            "type": "string",
        },
        "isDeliveryReceiptRequested": {
            "type": "boolean",
        },
        "isDraft": {
            "type": "boolean",
        },
        "isRead": {
            "type": "boolean",
        },
        "isReadReceiptRequested": {
            "type": "boolean",
        },
        "lastModifiedDateTime": {
            "type": "string",
            "format": "date-time",
        },
        "parentFolderId": {
            "type": "string",
            "minLength": 1,
        },
        "receivedDateTime": {
            "type": "string",
            "format": "date-time",
        },
        "replyTo": {
            "$ref": "#/definitions/optionalRecipients",
        },
        "sender": {
            "$ref": "#/definitions/recipient",
        },
        "sentDateTime": {
            "type": "string",
            "format": "date-time",
        },
        "subject": {
            "type": "string",
        },
        "toRecipients": {
            "$ref": "#/definitions/recipients",
        },
        "uniqueBody": {
            "$ref": "#/definitions/itemBody",
        },
        "webLink": {
            "type": "string",
        },
        "extensions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                    },
                },
                "required": [
                    "id",
                ],
                "additionalProperties": False,
            },
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
                            "type": "string",
                        },
                    },
                },
                "additionalProperties": False,
            },
        },
        "singleValueExtendedProperties": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                    },
                    "value": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}

# move or copy action on folder
_move_or_copy_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "destinationId": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": [
        "destinationId",
    ],
}

create_schema_validator = jsonschema.Draft4Validator(_create_schema)
update_schema_validator = jsonschema.Draft4Validator(_update_schema)
move_or_copy_schema_validator = jsonschema.Draft4Validator(_move_or_copy_schema)
