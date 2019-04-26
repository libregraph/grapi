# SPDX-License-Identifier: AGPL-3.0-or-later


def assert_create_item(client, user, data, url):
    result = client.simulate_get(url, headers=user.auth_header)
    assert result.status_code == 200
    assert len(result.json['value']) == 0

    result = client.simulate_post(url, headers=user.auth_header, json=data)
    assert result.status_code == 200

    result = client.simulate_get(url, headers=user.auth_header)
    assert result.status_code == 200
    assert len(result.json['value']) == 1


def test_get(client, user):
    # TODO(jelle): general get class? Inherit falcon test client?
    url = '/api/gc/v1/me'
    result = client.simulate_get(url, headers=user.auth_header)
    assert result.status_code == 200
    assert result.headers['content-type'] == 'application/json'

    assert result.json['displayName'] == user.name
    assert result.json['mail'] == user.email
    assert url in result.json['@odata.context']

    url = '/api/gc/v1/users/{}'.format(result.json['id'])
    result = client.simulate_get(url, headers=user.auth_header)
    assert result.status_code == 200
    assert result.headers['content-type'] == 'application/json'

    assert result.json['displayName'] == user.name
    assert result.json['mail'] == user.email
    assert url in result.json['@odata.context']


def test_list(client, user):
    url = '/api/gc/v1/users'
    result = client.simulate_get(url, headers=user.auth_header)

    assert result.status_code == 200
    assert result.headers['content-type'] == 'application/json'
    assert len(result.json['value']) == 1

    result_user = result.json['value'][0]
    assert result_user['userPrincipalName'] == user.name


def test_create_message(client, user, json_message):
    result = client.simulate_get('/api/gc/v1/me/mailFolders/drafts', headers=user.auth_header)
    assert result.status_code == 200
    assert result.json['totalItemCount'] == 0

    result = client.simulate_post('/api/gc/v1/me/messages', headers=user.auth_header, json=json_message)
    assert result.status_code == 200

    result = client.simulate_get('/api/gc/v1/me/mailFolders/drafts', headers=user.auth_header)
    assert result.status_code == 200
    assert result.json['totalItemCount'] == 1


def test_list_message(client, user):
    result = client.simulate_get('/api/gc/v1/me/messages', headers=user.auth_header)
    assert result.status_code == 200
    assert len(result.json['value']) == 0


def test_send_message(client, user, json_message):
    result = client.simulate_post('/api/gc/v1/me/messages', headers=user.auth_header, json=json_message)
    assert result.status_code == 200
    message_id = result.json['id']

    result = client.simulate_get('/api/gc/v1/me/messages/{}'.format(message_id), headers=user.auth_header)
    assert result.status_code == 200
    data = {
        'message': result
    }

    # TODO(jelle): broken in python-kopano
    #result = client.simulate_post('/api/gc/v1/me/sendMail', headers=user.auth_header, json=data)
    #assert result.status_code == 202


def test_list_contact_folders(client, user):
    result = client.simulate_get('/api/gc/v1/me/contactFolders', headers=user.auth_header)
    # Contact folders and Suggested Contacts
    len(result.json['value']) == 2


def test_create_contact(client, user, json_contact):
    assert_create_item(client, user, json_contact, '/api/gc/v1/me/contacts')


def test_list_contacts(client, user):
    result = client.simulate_get('/api/gc/v1/me/contacts', headers=user.auth_header)
    assert result.status_code == 200
    assert len(result.json['value']) == 0


def test_calendar(client, user):
    result = client.simulate_get('/api/gc/v1/me/calendar', headers=user.auth_header)
    assert result.status_code == 200
    assert result.json['displayName'] == 'Calendar'


def test_list_calendars(client, user):
    result = client.simulate_get('/api/gc/v1/me/calendars', headers=user.auth_header)
    assert result.status_code == 200
    assert len(result.json['value']) == 1
    assert result.json['value'][0]['displayName'] == 'Calendar'


def test_list_calendarview(client, user):
    result = client.simulate_get('/api/gc/v1/me/calendarView',
                                 headers=user.auth_header,
                                 query_string='startDateTime=2018-06-01T00:00:00.0000000Z&endDateTime=2018-07-01T00:00:00.0000000Z')
    assert result.status_code == 200
    assert len(result.json['value']) == 0


def test_list_reminderview(client, user):
    result = client.simulate_get('/api/gc/v1/me/reminderView',
                                 headers=user.auth_header,
                                 query_string='startDateTime=2018-06-01T00:00:00.0000000Z&endDateTime=2018-07-01T00:00:00.0000000Z')
    assert result.status_code == 200
    assert len(result.json['value']) == 0


def test_create_event(client, user, json_event):
    assert_create_item(client, user, json_event, '/api/gc/v1/me/events')


def test_delta(client, user, create_user):
    result = client.simulate_get('/api/gc/v1/users/delta', headers=user.auth_header)
    _, deltatoken = result.json['@odata.deltaLink'].split('delta?')
    assert len(result.json['value']) == 1

    result = client.simulate_get('/api/gc/v1/users/delta', headers=user.auth_header, query_string=deltatoken)
    _, deltatoken = result.json['@odata.deltaLink'].split('delta?')
    assert len(result.json['value']) == 0

    # Create new user
    user2 = create_user('user2')

    result = client.simulate_get('/api/gc/v1/users/delta', headers=user.auth_header, query_string=deltatoken)
    _, deltatoken = result.json['@odata.deltaLink'].split('delta?')
    assert len(result.json['value']) == 1

    # Test remove user
    user2.server.delete(user2)

    result = client.simulate_get('/api/gc/v1/users/delta', headers=user.auth_header, query_string=deltatoken)
    assert len(result.json['value']) == 1
    assert result.json['value'][0]['@removed']['reason'] == 'deleted'


def test_photo(client, user):
    result = client.simulate_get('/api/gc/v1/me/photos', headers=user.auth_header)
    assert result.status_code == 200
    assert len(result.json['value']) == 0


def test_memberof(client, user):
    result = client.simulate_get('/api/gc/v1/me/memberOf', headers=user.auth_header)
    assert result.json['value'][0]['displayName'] == 'Everyone'


def test_query_param(client, user):
    result = client.simulate_get('/api/gc/v1/me', query_string='$top=1', headers=user.auth_header)
    assert result.status_code == 200

    # not a non-negative integer
    result = client.simulate_get('/api/gc/v1/me', query_string='$top=nope', headers=user.auth_header)
    assert result.status_code == 400

    # not a non-negative integer
    result = client.simulate_get('/api/gc/v1/me', query_string='$skip=nope', headers=user.auth_header)
    assert result.status_code == 400

    # duplicate
    result = client.simulate_get('/api/gc/v1/me', query_string='$top=2&$top=3', headers=user.auth_header)
    assert result.status_code == 400

    # '2?$top=3' not a non-negative number
    result = client.simulate_get('/api/gc/v1/me', query_string='$top=2?&$top=3', headers=user.auth_header)
    assert result.status_code == 400

    # Missing start/end date
    result = client.simulate_get('/api/gc/v1/me/calendarView', headers=user.auth_header)
    assert result.status_code == 400

    # Not a date
    result = client.simulate_get('/api/gc/v1/me/calendarView', query_string='startDateTime=aap&endDateTime=2018-07-01T00:00:00.0000000Z', headers=user.auth_header)
    assert result.status_code == 400
