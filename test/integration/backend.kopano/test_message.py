# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test kopano/messages resource."""
import pytest

FOLDER_URL = '/api/gc/v1/me/mailFolders/'
MESSAGES_URLS = [
    '/api/gc/v1/me/messages',
    '/api/gc/v1/users/{userid}/messages',
    '/api/gc/v1/me/mailFolders/drafts/messages',
    '/api/gc/v1/users/{userid}/mailFolders/drafts/messages',
    '/api/gc/v1/me/mailFolders/inbox/messages',
    '/api/gc/v1/users/{userid}/mailFolders/inbox/messages',
]
FOLDER_MESSAGES_URLS = [
    '/api/gc/v1/me/mailFolders/{folderid}/messages',
    '/api/gc/v1/users/{userid}/mailFolders/{folderid}/messages',
]
ACTION_MESSAGE_URLS = [
    '/api/gc/v1/me/mailFolders/{folderid}/messages/{messageid}/{action}',
    '/api/gc/v1/users/{userid}/mailFolders/{folderid}/messages/{messageid}/{action}',
]


def get_folder_id(client, user, display_name):
    """Return folder ID by displayName.

    Args:
        client (TestClient): conftest client variable.
        user (User): conftest user variable.
        display_name (str): folder displayName.

    Returns:
        str: folder ID.
    """
    response = client.simulate_get(FOLDER_URL, headers=user.auth_header)
    folders = response.json["value"]
    for folder in folders:
        if folder["displayName"].lower() == display_name.lower():
            return folder["id"]
    assert False


def get_a_message(client, user, base_url, folderid, index):
    """Get a message in a specific folder by index number.

    Args:
        client (TestClient): conftest client variable.
        user (User): conftest user variable.
        base_url (str): base URL for fmt ('{folderid}').
        folderid (str): folder ID.
        index (int): message index number.

    Returns:
        str: message ID.
    """
    response = client.simulate_get(
        base_url.format(userid=user.userid, folderid=folderid), headers=user.auth_header
    )
    return response.json["value"][index]["id"]


def get_count_of_messages(client, user, base_url, folderid):
    """Get count of messages on a specific folder.

    Args:
        client (TestClient): conftest client variable.
        user (User): conftest user variable.
        base_url (str): base URL for fmt ('{folderid}').
        folderid (str): folder ID.

    Returns:
        int: count of messages in the folder.
    """
    response = client.simulate_get(
        base_url.format(userid=user.userid, folderid=folderid), headers=user.auth_header
    )
    return len(response.json["value"])


def check_created_messages(messages, json_message):
    """Check created messages by the sample one.

    Args:
        messages (List[Dict]): list of messages.
        json_message (Dict): sample message content to compare with.
    """
    for message in messages:
        for key, value in json_message.items():
            # Ignore datetime and IDs and changeKey.
            if key.endswith("DateTime") or "id" in key.lower() or key == "changeKey":
                continue

            # isRead should be true.
            if key == "isRead":
                assert message[key]
                continue

            assert message[key] == value


@pytest.mark.parametrize("url", MESSAGES_URLS)
def test_on_post_messages(client, user, json_message, url):
    """Test on_post_messages endpoint(s)."""
    url = url.format(userid=user.userid)
    response = client.simulate_post(url, headers=user.auth_header, json=json_message)
    assert response.status_code == 201
    assert 'id' in response.json


@pytest.mark.parametrize("url", FOLDER_MESSAGES_URLS)
def test_on_post_folder(client, user, json_message, url):
    """Test on_post_folder endpoint(s)."""
    folderid = get_folder_id(client, user, "inbox")
    url = url.format(userid=user.userid, folderid=folderid)
    response = client.simulate_post(url, headers=user.auth_header, json=json_message)
    assert response.status_code == 201
    assert 'id' in response.json


@pytest.mark.parametrize("url", FOLDER_MESSAGES_URLS)
def test_on_get_item(client, user, url, json_message):
    """Test on_get_item endpoint(s)."""
    folderid = get_folder_id(client, user, "inbox")

    # Get a messageid.
    url = url.format(userid=user.userid, folderid=folderid)
    response = client.simulate_get(url, headers=user.auth_header)
    message_id = response.json["value"][0]["id"]

    # Get the message data.
    response = client.simulate_get("{}/{}".format(url, message_id), headers=user.auth_header)
    message = response.json

    check_created_messages([message], json_message)


@pytest.mark.parametrize(
    [
        "url",
        "action",
        "origin_folder_messages_count_expected_before",
        "destination_folder_messages_count_expected_before",
        "origin_folder_messages_count_expected_after",
        "destination_folder_messages_count_expected_after",
    ],
    [
        (FOLDER_MESSAGES_URLS[0], "copy", 4, 0, 4, 1),
        (FOLDER_MESSAGES_URLS[0], "copy", 4, 1, 4, 2),
        (FOLDER_MESSAGES_URLS[0], "move", 4, 2, 3, 3),
        (FOLDER_MESSAGES_URLS[0], "move", 3, 3, 2, 4),
    ]
)
def test_on_post_copy_and_move(
    client,
    user,
    url,
    action,
    origin_folder_messages_count_expected_before,
    destination_folder_messages_count_expected_before,
    origin_folder_messages_count_expected_after,
    destination_folder_messages_count_expected_after
):
    """Test on_post_copy_and_move endpoint(s)."""
    origin_folder_id = get_folder_id(client, user, "inbox")
    destination_folder_id = get_folder_id(client, user, "junk e-mail")

    # Before.
    origin_folder_messages_count = get_count_of_messages(
        client, user, url, origin_folder_id
    )
    destination_folder_messages_count = get_count_of_messages(
        client, user, url, destination_folder_id
    )
    assert origin_folder_messages_count == origin_folder_messages_count_expected_before
    assert destination_folder_messages_count == destination_folder_messages_count_expected_before

    message_id = get_a_message(client, user, url, origin_folder_id, 0)

    copy_url = ACTION_MESSAGE_URLS[1].format(
        userid=user.userid, folderid=origin_folder_id, messageid=message_id, action=action
    )
    response = client.simulate_post(
        copy_url, headers=user.auth_header, json={"destinationId": destination_folder_id}
    )
    assert response.status_code == 201

    # After.
    origin_folder_messages_count = get_count_of_messages(
        client, user, url, origin_folder_id
    )
    destination_folder_messages_count = get_count_of_messages(
        client, user, url, destination_folder_id
    )
    assert origin_folder_messages_count == origin_folder_messages_count_expected_after
    assert destination_folder_messages_count == destination_folder_messages_count_expected_after


@pytest.mark.parametrize("url", FOLDER_MESSAGES_URLS)
def test_on_patch_item(client, user, url, json_message):
    """Test on_patch_item endpoint(s)."""
    folderid = get_folder_id(client, user, "inbox")

    # Get a message ID.
    url = url.format(userid=user.userid, folderid=folderid)
    response = client.simulate_get(url, headers=user.auth_header)
    message_id = response.json["value"][0]["id"]

    updated_fields = {
        "subject": "new subject",
        "body": {
            "contentType": "html",
            "content": "new content",
        },
        "from": {
            "emailAddress": {
                "name": "New user",
                "address": "user@domain.com",
            },
        },
        "replyTo": [],
    }

    # Patch the message data with new data.
    response = client.simulate_patch(
        "{}/{}".format(url, message_id),
        headers=user.auth_header,
        json=updated_fields
    )
    assert response.status_code == 200
    message = response.json
    json_message.update(**updated_fields)
    json_message["bodyPreview"] = updated_fields["body"]["content"]
    json_message["replyTo"] = []
    check_created_messages([message], json_message)

    # Patch the message data with new data but with empty replyTo.
    updated_fields["replyTo"] = []
    response = client.simulate_patch(
        "{}/{}".format(url, message_id),
        headers=user.auth_header,
        json=updated_fields
    )
    assert response.status_code == 200
    message = response.json
    json_message.update(**updated_fields)
    json_message["bodyPreview"] = updated_fields["body"]["content"]
    json_message["replyTo"] = []
    check_created_messages([message], json_message)


@pytest.mark.parametrize(
    [
        "url",
        "count_of_messages_exists",
        "count_of_messages_removed",
    ],
    [
        (FOLDER_MESSAGES_URLS[0], 4, 2),
        (FOLDER_MESSAGES_URLS[1], 2, 2),
    ]
)
def test_on_delete_item(
    client,
    user,
    json_message,
    url,
    count_of_messages_exists,
    count_of_messages_removed
):
    """Test on_delete_item endpoint(s)."""
    folderid = get_folder_id(client, user, "junk e-mail")

    url = url.format(userid=user.userid, folderid=folderid)

    # Before.
    assert get_count_of_messages(client, user, url, folderid) == count_of_messages_exists

    response = client.simulate_get(url, headers=user.auth_header)
    messages = response.json["value"][:count_of_messages_removed]
    for message in messages:
        response = client.simulate_delete(
            "{}/{}".format(url, message["id"]),
            headers=user.auth_header
        )
        assert response.status_code == 204

    # After.
    expected_count = count_of_messages_exists - count_of_messages_removed
    assert get_count_of_messages(client, user, url, folderid) == expected_count
