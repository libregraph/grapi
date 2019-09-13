# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import json
import os

import pytest

from falcon.testing import TestClient

import kopano

from grapi.api.v1 import RestAPI

DATA_DIR = '{}/data'.format(os.path.dirname(os.path.realpath(__file__)))
BACKEND = 'kopano'
API = '/api/gc/v1'

USERNAME1 = 'user1'
PASSWORD1 = 'user1'
EMAIL1 = 'grapi@kopano.io'
KOPANO_SSLKEY_FILE = os.getenv('KOPANO_SSLKEY_FILE', '')
KOPANO_SSLKEY_PASS = os.getenv('KOPANO_SSLKEY_PASS', '')


class Options:
    with_experimental = True
    auth_basic = True
    with_metrics = False


def create_auth_header(username, password):
    b64 = base64.b64encode('{}:{}'.format(username, password).encode())
    return {'Authorization': 'Basic {}'.format(b64.decode())}


# https://falcon.readthedocs.io/en/stable/api/testing.html
@pytest.fixture(scope='module')
def client():
    return TestClient(RestAPI(options=Options(), backends=[BACKEND]))


@pytest.fixture()
def user():
    if KOPANO_SSLKEY_FILE:
        admin_server = kopano.Server(parse_args=False, sslkey_file=KOPANO_SSLKEY_FILE, sslkey_pass=KOPANO_SSLKEY_PASS)
        try:
            admin_server.user(USERNAME1).create_store()
        except kopano.errors.DuplicateError:
            pass


    server = kopano.Server(parse_args=False, auth_user=USERNAME1, auth_pass=PASSWORD1)
    user = server.user(USERNAME1)
    user.auth_header = create_auth_header(USERNAME1, PASSWORD1)
    yield user

    if KOPANO_SSLKEY_FILE:
        admin_server.user(USERNAME1).unhook()
    else:
        [f.empty() for f in user.folders()]


@pytest.fixture
def create_user():
    users = []
    server = kopano.Server(parse_args=False)

    def _create_user(name):
        user = server.create_user(name, email='{}@kopano.io'.format(name), password=name)
        user.auth_header = create_auth_header(name, name)
        users.append(user)
        return user

    yield _create_user

    for user in users:
        # Test could have removed a user
        try:
            server.delete(user)
        except kopano.errors.NotFoundError:
            pass


@pytest.fixture()
def auth_header():
    b64 = base64.b64encode('{}:{}'.format(USERNAME1, PASSWORD1).encode())
    return {'Authorization': 'Basic {}'.format(b64.decode())}


@pytest.fixture()
def json_message():
    return json.load(open('{}/message'.format(DATA_DIR)))


@pytest.fixture()
def json_contact():
    return json.load(open('{}/contact'.format(DATA_DIR)))


@pytest.fixture()
def json_event():
    return json.load(open('{}/event'.format(DATA_DIR)))


@pytest.fixture()
def json_event_daily():
    return json.load(open('{}/event_daily'.format(DATA_DIR)))


@pytest.fixture()
def calendar_entryid(user):
    return user.calendar.entryid
