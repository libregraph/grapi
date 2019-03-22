# SPDX-License-Identifier: AGPL-3.0-or-later


def test_get_message(client):
    result = client.simulate_get('/api/gc/v1/me/messages')
    assert result.status_code == 200
    assert result.headers['content-type'] == 'application/json'
