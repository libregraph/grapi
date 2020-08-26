# SPDX-License-Identifier: AGPL-3.0-or-later


def test_get_message(client):
    result = client.simulate_get('/api/gc/v1/me/messages')
    assert result.status_code == 200
    assert result.headers['content-type'] == 'application/json'


def test_batch_invalid(client):
    data = {'this': 'invalid'}
    result = client.simulate_post('/api/gc/v1/$batch', json=data)
    assert result.status_code == 400


def test_batch(client):
    data = {'requests': [{'id': '1', 'method': 'GET', 'url': '/api/gc/v1/me/messages'}]}

    result = client.simulate_post('/api/gc/v1/$batch', json=data)
    assert result.status_code == 200
    assert result.json[0]['id'] == data['requests'][0]['id']
    assert result.json[0]['status'] == 200
    assert result.json[0]['body']['@odata.context'] == data['requests'][0]['url']
