# SPDX-License-Identifier: AGPL-3.0-or-later


def assert_create_folder(client, user, name):
    url = '/api/gc/v1/me/mailFolders/inbox/childFolders'

    data = {
        'displayName': name,
    }

    response = client.simulate_post(url,
                                    json=data,
                                    headers=user.auth_header)
    assert response.status_code == 201
    return response.json['id']


def test_inbox(client, user):
    url = '/api/gc/v1/me/mailFolders/inbox/'
    response = client.simulate_get(url, headers=user.auth_header)
    assert response.status_code == 200
    data = response.json
    assert data['displayName'] == 'Inbox'
    assert data['totalItemCount'] == 0
    assert data['unreadItemCount'] == 0
    assert data['childFolderCount'] == 0


def test_create_folder(client, user):
    name = 'grapi'
    id_ = assert_create_folder(client, user, name)

    # Inbox folder updated
    url = '/api/gc/v1/me/mailFolders/inbox/'
    response = client.simulate_get(url, headers=user.auth_header)
    assert response.status_code == 200
    assert response.json['childFolderCount'] == 1

    # Folder details visible
    url = '/api/gc/v1/me/mailFolders/{}'.format(id_)
    response = client.simulate_get(url, headers=user.auth_header)
    data = response.json
    assert data['displayName'] == name
    assert data['totalItemCount'] == 0
    assert data['unreadItemCount'] == 0
    assert data['childFolderCount'] == 0


def test_delete(client, user):
    url = '/api/gc/v1/me/mailFolders/{}'
    name = 'grapi'
    id_ = assert_create_folder(client, user, name)

    response = client.simulate_delete(url.format(id_), headers=user.auth_header)
    assert response.status_code == 204


# TODO: enable when inbox can't be deleted
def xtest_delete_special_folder(client, user):
    url = '/api/gc/v1/me/mailFolders/inbox/'
    response = client.simulate_get(url, headers=user.auth_header)
    assert response.status_code == 200
    id_ = response.json['id']

    url = '/api/gc/v1/me/mailFolders/{}'
    response = client.simulate_delete(url.format(id_), headers=user.auth_header)
    assert response.status_code == 400

    url = '/api/gc/v1/me/mailFolders/inbox'
    response = client.simulate_delete(url, headers=user.auth_header)
    assert response.status_code == 400


def test_special_folders(client, user):
    url = '/api/gc/v1/me/mailFolders/{}'
    folders = [('junkemail', 'Junk E-mail'), ('deleteditems', 'Deleted Items')]
    for folder in folders:
        response = client.simulate_get(url.format(folder[0]), headers=user.auth_header)
        assert response.status_code == 200
        assert response.json['displayName'] == folder[1]


def test_create_message(client, user, json_message):
    url = '/api/gc/v1/me/mailFolders/inbox/messages'
    response = client.simulate_post(url, headers=user.auth_header, json=json_message)
    assert response.status_code == 201
    assert response.json['subject'] == json_message['subject']
    assert not response.json['isRead']

    url = '/api/gc/v1/me/mailFolders/inbox/'
    response = client.simulate_get(url, headers=user.auth_header)
    assert response.status_code == 200
    assert response.json['totalItemCount'] == 1


def test_copy(client, user):
    folder1 = assert_create_folder(client, user, 'folder1')
    dest = assert_create_folder(client, user, 'destination')
    data = {
        'destinationId': dest
    }

    url = '/api/gc/v1/me/mailFolders/{}/copy'.format(folder1)
    response = client.simulate_post(url, headers=user.auth_header, json=data)
    assert response.status_code == 200

    response = client.simulate_get('/api/gc/v1/me/mailFolders/{}'.format(dest), headers=user.auth_header)
    assert response.status_code == 200
    assert response.json['childFolderCount'] == 1

    # Original folder copied
    response = client.simulate_get('/api/gc/v1/me/mailFolders/inbox', headers=user.auth_header)
    assert response.status_code == 200
    assert response.json['childFolderCount'] == 2


def test_move(client, user):
    folder1 = assert_create_folder(client, user, 'folder1')
    dest = assert_create_folder(client, user, 'destination')
    data = {
        'destinationId': dest
    }

    url = '/api/gc/v1/me/mailFolders/{}/move'.format(folder1)
    response = client.simulate_post(url, headers=user.auth_header, json=data)
    assert response.status_code == 200

    response = client.simulate_get('/api/gc/v1/me/mailFolders/{}'.format(dest), headers=user.auth_header)
    assert response.status_code == 200
    assert response.json['childFolderCount'] == 1

    # Original folder moved
    response = client.simulate_get('/api/gc/v1/me/mailFolders/inbox', headers=user.auth_header)
    assert response.status_code == 200
    assert response.json['childFolderCount'] == 1
