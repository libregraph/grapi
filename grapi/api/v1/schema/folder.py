"""Folder JSON schema."""
import jsonschema

# create or update folder
_create_or_update_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "displayName": {
            "type": "string",
            "minLength": 1,
        },
    },
    "required": [
        "displayName",
    ],
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

create_or_update_schema_validator = jsonschema.Draft4Validator(_create_or_update_schema)
move_or_copy_schema_validator = jsonschema.Draft4Validator(_move_or_copy_schema)
