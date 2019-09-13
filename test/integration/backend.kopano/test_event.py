# SPDX-License-Identifier: AGPL-3.0-or-later


def test_list_empty_events(client, user):
    url = '/api/gc/v1/me/events/'

    response = client.simulate_get(url, headers=user.auth_header)
    assert response.status_code == 200
    assert len(response.json['value']) == 0
    assert response.headers['content-type'] == 'application/json'


def test_create_event(client, user, json_event):
    url = '/api/gc/v1/me/events'
    response = client.simulate_post(url, headers=user.auth_header, json=json_event)

    assert response.status_code == 200
    assert 'id' in response.json
    assert response.json['@odata.context'] == url


def test_create_recurrence(client, user, json_event_daily):
    url = '/api/gc/v1/me/events'
    response = client.simulate_post(url, headers=user.auth_header, json=json_event_daily)

    assert response.status_code == 200
    assert response.json['@odata.context'] == url
    assert 'id' in response.json

    # TODO: Check expanded recurrence


def test_update(client, user, json_event):
    url = '/api/gc/v1/me/events/'

    response = client.simulate_post(url, headers=user.auth_header, json=json_event)
    assert response.status_code == 200

    update = {
        'subject': 'new subject'
    }

    id_ = response.json['id']
    response = client.simulate_patch(url + id_, json=update, headers=user.auth_header)
    assert response.status_code == 200

    response = client.simulate_get(url + id_, headers=user.auth_header)
    assert response.json['subject'] == 'new subject'


def test_delete(client, user, json_event):
    url = '/api/gc/v1/me/events/'

    response = client.simulate_post(url, headers=user.auth_header, json=json_event)
    assert response.status_code == 200

    id_ = response.json['id']
    response = client.simulate_delete(url + id_, headers=user.auth_header)
    assert response.status_code == 204

    response = client.simulate_get(url + id_, headers=user.auth_header)
    # TODO: check if correct
    assert response.status_code == 400

def test_folders(client, user):
    response = client.simulate_get('/api/gc/v1/me/calendars',
                                   headers=user.auth_header)
    assert response.status_code == 200
    assert len(response.json['value']) == 1


def test_recurrence_instances(client, user, calendar_entryid, json_event_daily):
    '''recurrence every day starting 2018-06-05 ends after 40 occurences.'''
    url = '/api/gc/v1/me/events/'

    response = client.simulate_post(url, headers=user.auth_header, json=json_event_daily)
    assert response.status_code == 200

    id_ = response.json['id']

    url = '/api/gc/v1/me/calendars/{}/calendarView/'.format(calendar_entryid)
    response = client.simulate_get(url,
                                   headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z&$select=subject,isAllDay,start,end,responseStatus,type,seriesMasterId')
    assert response.status_code == 200

    for occ in response.json['value']:
        assert occ['subject'] == 'daily'
        assert occ['seriesMasterId'] == id_


def test_delete_instance(client, user, calendar_entryid, json_event_daily):
    url = '/api/gc/v1/me/events/'

    response = client.simulate_post(url, headers=user.auth_header, json=json_event_daily)
    assert response.status_code == 200

    id_ = response.json['id']

    url = '/api/gc/v1/me/calendars/{}/calendarView/'.format(calendar_entryid)
    response = client.simulate_get(url,
                                   headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z')
    assert response.status_code == 200
    occurences = len(response.json['value'])
    occ = response.json['value'][0]
    id_ = occ['id']

    # remove the first instance
    response = client.simulate_delete('/api/gc/v1/me/events/{}'.format(id_),
                                      headers=user.auth_header)
    assert response.status_code == 204

    url = '/api/gc/v1/me/calendars/{}/calendarView/'.format(calendar_entryid)
    response = client.simulate_get(url,
                                   headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z')
    assert response.status_code == 200
    assert len(response.json['value']) == occurences - 1
    # Verify it's really deleted
    assert any(occ['id'] == id_ for occ in response.json['value']) == False


def test_update_instance(client, user, calendar_entryid, json_event_daily):
    url = '/api/gc/v1/me/events/'

    response = client.simulate_post(url, headers=user.auth_header, json=json_event_daily)
    assert response.status_code == 200

    id_ = response.json['id']
    url = '/api/gc/v1/me/calendars/{}/calendarView/'.format(calendar_entryid)
    response = client.simulate_get(url,
                                   headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z')
    assert response.status_code == 200
    occ = response.json['value'][0]
    id_ = occ['id']

    update = {
        'subject': 'new subject'
    }

    response = client.simulate_patch('/api/gc/v1/me/events/{}'.format(id_),
                                    json=update,
                                    headers=user.auth_header)
    assert response.status_code == 200

    url = '/api/gc/v1/me/events/'
    response = client.simulate_get(url + id_, headers=user.auth_header)
    assert response.json['subject'] == 'new subject'

    url = '/api/gc/v1/me/calendars/{}/calendarView/'.format(calendar_entryid)
    response = client.simulate_get(url,
                                   headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z')
    assert response.status_code == 200
    occ = response.json['value'][0]
    assert occ['subject'] == 'new subject'
