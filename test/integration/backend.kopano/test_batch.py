"""Test $batch requests."""
from uuid import uuid4

import pytest

URL = "/api/gc/v1/$batch"


def send_and_assert_request(client, user, batch, expected_item_status_code=None):
    """Send and assert on the general fields.

    Returns:
        Dict: response in JSON format.
    """
    response = client.simulate_post(URL, headers=user.auth_header, json=batch)
    assert response.status_code == 200
    response_json = response.json
    assert len(response_json) == 3
    for response_json_item in response_json:
        # Response data.
        assert response_json_item["id"]
        if expected_item_status_code:
            assert response_json_item["status"] == expected_item_status_code
        else:
            assert response_json_item["status"]
        assert response_json_item["headers"] == {"content-type": "application/json"}

    return response_json


def test_get_requests(client, user, json_batch):
    """Test first batch request."""
    batch = json_batch["batch"][0]
    response = client.simulate_post(URL, headers=user.auth_header, json=batch)
    assert response.status_code == 200
    response_json = response.json
    assert len(response_json) == 3
    for response_json_item in response_json:
        # Response data.
        assert response_json_item["id"]
        assert response_json_item["status"] == 200
        assert response_json_item["headers"] == {"content-type": "application/json"}

        # User data.
        assert response_json_item["body"]["id"]
        assert response_json_item["body"]["displayName"]
        assert response_json_item["body"]["mobilePhone"]


@pytest.mark.parametrize(
    ["batch_index", "expected_failure"],
    [(1, True), (2, False)]
)
def test_wrong_get_requests(client, user, json_batch, batch_index, expected_failure):
    """Test third batch request."""
    batch = json_batch["batch"][batch_index]
    response_json = send_and_assert_request(client, user, batch)

    assert response_json[0]["status"] == 404
    assert response_json[0]["body"] == {"error": {"code": 404, "message": "Not found."}}

    # Chain of failure(s).
    assert response_json[1]["status"] == 424
    assert response_json[1]["body"] == {"error": {"code": 424, "message": "Failed dependency - ID: 1"}}

    if expected_failure:
        assert response_json[2]["status"] == 424
        assert response_json[2]["body"] == {"error": {"code": 424, "message": "Failed dependency - ID: 2"}}
    else:
        # Independent GET request (user data)
        assert response_json[2]["body"]["id"]
        assert response_json[2]["body"]["displayName"]
        assert response_json[2]["body"]["mobilePhone"]


def test_get_delete_post_methods(client, user, json_batch):
    """Test forth batch request."""
    # Create a folder manually to add its ID to the batch request.
    response = client.simulate_post(
        "/api/gc/v1/me/mailFolders", headers=user.auth_header, json={"displayName": uuid4().hex}
    )
    folder_id = response.json["id"]
    new_folder_name = uuid4().hex

    batch = json_batch["batch"][3]
    batch["requests"][1]["url"] = batch["requests"][1]["url"].format(folder_id)
    batch["requests"][2]["body"]["displayName"] = new_folder_name
    response_json = send_and_assert_request(client, user, batch)

    # First request (GET).
    assert response_json[0]["body"]["id"]
    assert response_json[0]["body"]["displayName"]
    assert response_json[0]["body"]["mobilePhone"]

    # Third request (POST).
    assert response_json[1]["status"] == 201
    assert response_json[1]["body"]["id"]
    assert response_json[1]["body"]["parentFolderId"]
    assert response_json[1]["body"]["displayName"] == new_folder_name
    assert response_json[1]["body"]["unreadItemCount"] == 0

    # Second request (DELETE)
    assert response_json[2]["status"] == 204
    assert response_json[2]["body"] is None
