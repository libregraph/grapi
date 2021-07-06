# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

URLS = ['/api/gc/v1/me/events', '/api/gc/v1/me/calendars/calendar/events']


def assert_create_event(client, user, event, url):
    response = client.simulate_post(url, headers=user.auth_header, json=event)
    assert response.status_code == 200
    return response.json['id']


@pytest.mark.parametrize("url", URLS)
def test_list_empty_events(client, user, url):
    response = client.simulate_get(url, headers=user.auth_header)
    assert response.status_code == 200
    assert len(response.json['value']) == 0
    assert response.headers['content-type'] == 'application/json'


@pytest.mark.parametrize("url", URLS)
def test_create_event(client, user, json_event, url):
    response = client.simulate_post(url, headers=user.auth_header, json=json_event)

    assert response.status_code == 200
    assert 'id' in response.json
    assert response.json['@odata.context'] == url
    assert response.json['showAs'] == 'busy'


@pytest.mark.parametrize("url", URLS)
def test_create_recurrence(client, user, json_event_daily, url):
    response = client.simulate_post(url, headers=user.auth_header, json=json_event_daily)

    assert response.status_code == 200
    assert response.json['@odata.context'] == url
    assert 'id' in response.json

    # TODO: Check expanded recurrence


@pytest.mark.parametrize("url", URLS)
def test_create_recurrence_weekly(client, user, json_event_weekly, url):
    response = client.simulate_post(url, headers=user.auth_header, json=json_event_weekly)

    assert response.status_code == 200
    assert response.json['@odata.context'] == url
    assert response.json['isAllDay']

    # TODO: Check expanded recurrence


@pytest.mark.parametrize("url", URLS)
def test_post_event_accept_not_data(client, user, json_event, url):
    id_ = assert_create_event(client, user, json_event, url)
    response = client.simulate_post(url + '/{}/accept'.format(id_), headers=user.auth_header)
    assert response.status_code == 202


@pytest.mark.parametrize("url", URLS)
def test_get_event_malformed(client, user, url):
    response = client.simulate_get(url + '/malformed', headers=user.auth_header)
    assert response.status_code == 400
    assert 'Event id is malformed' in response.text


@pytest.mark.parametrize("url", URLS)
def test_get_event_attachments(client, user, json_event, url):
    id_ = assert_create_event(client, user, json_event, url)
    response = client.simulate_get(url + '/{}/attachments'.format(id_), headers=user.auth_header)
    assert response.status_code == 200
    assert not response.json['value']


@pytest.mark.parametrize("url", URLS)
def test_get_event_instances(client, user, json_event, url):
    id_ = assert_create_event(client, user, json_event, url)

    response = client.simulate_get(url + '/{}/instances'.format(id_), headers=user.auth_header)
    # requires time window specified by query string StartDateTime and EndDateTime
    assert response.status_code == 400

    response = client.simulate_get(url + '/{}/instances'.format(id_), headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z')
    assert response.status_code == 200
    # Single event has one instance
    assert len(response.json['value']) == 1


@pytest.mark.parametrize("url", URLS)
def test_update(client, user, json_event, url):
    response = client.simulate_post(url, headers=user.auth_header, json=json_event)
    assert response.status_code == 200

    update = {
        'subject': 'new subject'
    }

    id_ = response.json['id']
    response = client.simulate_patch(url + '/' + id_, json=update, headers=user.auth_header)
    assert response.status_code == 200

    response = client.simulate_get(url + '/' + id_, headers=user.auth_header)
    assert response.json['subject'] == 'new subject'


@pytest.mark.parametrize("url", URLS)
def test_delete(client, user, json_event, url):
    response = client.simulate_post(url, headers=user.auth_header, json=json_event)
    assert response.status_code == 200

    id_ = response.json['id']
    response = client.simulate_delete(url + '/' + id_, headers=user.auth_header)
    assert response.status_code == 204

    response = client.simulate_get(url + '/' + id_, headers=user.auth_header)
    assert response.status_code == 404


def test_folders(client, user):
    response = client.simulate_get('/api/gc/v1/me/calendars',
                                   headers=user.auth_header)
    assert response.status_code == 200
    assert len(response.json['value']) == 1


@pytest.mark.parametrize("url", URLS)
def test_recurrence_instances(client, user, calendar_entryid, json_event_daily, url):
    '''recurrence every day starting 2018-06-05 ends after 40 occurences.'''
    response = client.simulate_post(url, headers=user.auth_header, json=json_event_daily)
    assert response.status_code == 200

    id_ = response.json['id']

    url = '/api/gc/v1/me/calendars/{}/calendarView/'.format(calendar_entryid)
    response = client.simulate_get(url,
                                   headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z&$select=subject,isAllDay,start,end,responseStatus,type,seriesMasterId')
    assert response.status_code == 200

    for occ in response.json['value']:
        if occ["seriesMasterId"] != id_:
            continue
        assert occ['subject'] == "daily"


@pytest.mark.parametrize("url", URLS)
def test_delete_instance(client, user, calendar_entryid, json_event_daily, url):
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
    assert len(response.json['value']) == occurences
    # Verify it's really deleted
    assert not any(occ['id'] == id_ for occ in response.json['value'])


@pytest.mark.parametrize("url", URLS)
def test_update_instance(client, user, calendar_entryid, json_event_daily, url):
    response = client.simulate_post(url, headers=user.auth_header, json=json_event_daily)
    assert response.status_code == 200

    id_ = response.json['id']
    calendar_url = '/api/gc/v1/me/calendars/{}/calendarView/'.format(calendar_entryid)
    response = client.simulate_get(calendar_url,
                                   headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z')
    assert response.status_code == 200
    occ = response.json['value'][0]
    id_ = occ['id']

    update = {
        'subject': 'new subject'
    }

    response = client.simulate_patch(url + '/' + id_,
                                     json=update,
                                     headers=user.auth_header)
    assert response.status_code == 200

    response = client.simulate_get(url + '/' + id_, headers=user.auth_header)
    assert response.json['subject'] == 'new subject'

    calendar_url = '/api/gc/v1/me/calendars/{}/calendarView/'.format(calendar_entryid)
    response = client.simulate_get(calendar_url,
                                   headers=user.auth_header,
                                   query_string='startDateTime=2018-06-04T00:00:00.0000000Z&endDateTime=2018-06-10T00:00:00.0000000Z')
    assert response.status_code == 200
    occ = response.json['value'][0]
    assert occ['subject'] == 'new subject'


@pytest.mark.parametrize("url", URLS)
def test_tentatively_accept(client, user, json_event_daily, url):
    event_id = assert_create_event(client, user, json_event_daily, url)
    tentatively_accept_url = "{}/{}/tentativelyAccept".format(url, event_id)
    data = {
        "comment": "test comment",
        "sendResponse": True,
    }
    resp = client.simulate_post(tentatively_accept_url, headers=user.auth_header, json=data)
    assert resp.status_code == 202


@pytest.mark.parametrize("url", URLS)
def test_tentatively_accept_with_new_proposed_time(client, user, json_event_daily, url):
    event_id = assert_create_event(client, user, json_event_daily, url)
    tentatively_accept_url = "{}/{}/tentativelyAccept".format(url, event_id)
    data = {
        "comment": "test comment",
        "sendResponse": True,
        "proposedNewTime": {
            "start": {
                "dateTime": "2021-01-01T12:00:00+00:00",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2021-01-01T13:00:00+00:00",
                "timeZone": "UTC"
            }
        }
    }
    resp = client.simulate_post(tentatively_accept_url, headers=user.auth_header, json=data)
    assert resp.status_code == 202


@pytest.mark.parametrize("url", URLS)
def test_tentatively_accept_with_new_proposed_time_error(client, user, json_event_daily, url):
    json_event_daily["sendResponse"] = False
    event_id = assert_create_event(client, user, json_event_daily, url)
    tentatively_accept_url = "{}/{}/tentativelyAccept".format(url, event_id)
    data = {
        "comment": "test comment",
        "sendResponse": True,
        "proposedNewTime": {
            "start": {
                "dateTime": "2021-01-01T12:00:00+00:00",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2021-01-01T13:00:00+00:00",
                "timeZone": "UTC"
            }
        }
    }
    resp = client.simulate_post(tentatively_accept_url, headers=user.auth_header, json=data)
    assert resp.status_code == 400
    assert resp.json == {"title": "400 Bad Request", "description": "Event disabled sendResponse"}


@pytest.mark.parametrize("url", URLS)
def test_tentatively_accept_error(client, user, json_event_daily, url):
    json_event_daily["allowNewTimeProposals"] = False
    event_id = assert_create_event(client, user, json_event_daily, url)
    tentatively_accept_url = "{}/{}/tentativelyAccept".format(url, event_id)
    data = {
        "comment": "test comment",
        "sendResponse": True,
        "proposedNewTime": {
            "start": {
                "dateTime": "2021-01-01T12:00:00+00:00",
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": "2021-01-01T13:00:00+00:00",
                "timeZone": "UTC"
            }
        }
    }
    resp = client.simulate_post(tentatively_accept_url, headers=user.auth_header, json=data)
    assert resp.status_code == 400
    assert resp.json == {"title":"400 Bad Request", "description":"Event disabled requesting proposedNewTime"}

