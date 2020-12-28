"""Attachment JSON schema."""
import jsonschema

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


file_attachment_schema_validator = jsonschema.Draft4Validator(_file_attachment_schema)
item_attachment_schema_validator = jsonschema.Draft4Validator(_item_attachment_schema)
reference_attachment_schema_validator = jsonschema.Draft4Validator(_reference_attachment_schema)
