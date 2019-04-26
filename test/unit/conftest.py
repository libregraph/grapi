# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest

from falcon import testing

from grapi.api.v1 import RestAPI


BACKEND = 'mock'


# https://falcon.readthedocs.io/en/stable/api/testing.html
@pytest.fixture(scope='module')
def client():
    return testing.TestClient(RestAPI(backends=[BACKEND]))

