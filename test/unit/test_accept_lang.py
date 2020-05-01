# SPDX-License-Identifier: AGPL-3.0-or-later

from grapi.mfr.utils import parse_accept_language


def test_empty():
    assert parse_accept_language('') == []


def test_one_language():
    assert parse_accept_language('fr-CA') == [('fr-ca', 1.0)]


def test_multiple_languages():
    assert parse_accept_language('de-AT , de') == [('de-at', 1.0), ('de', 0.99)]


def test_quality():
    assert parse_accept_language('de-AT , de ; q=0.8') == [('de-at', 1.0), ('de', 0.8)]


def test_normal():
    assert parse_accept_language('de-DE,ar-TN;q=0.7,de-AT;q=0.3') == [('de-de', 1.0), ('ar-tn', 0.7), ('de-at', 0.3)]
