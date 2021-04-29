"""Test backend/kopano/message module."""
from unittest.mock import Mock

from grapi.backend.kopano import message


def test_set_recipients_normal():
    """Test set_to_recipients with a correct data."""
    item = Mock()
    to_recipients = [
        {"emailAddress": {"name": "user1", "address": "user1@kopano.com"}},
        {"emailAddress": {"address": "user2@kopano.com"}},
    ]
    message.set_recipients(item, to_recipients)
    assert item.to == "user1 <user1@kopano.com>;user2@kopano.com <user2@kopano.com>"


def test_set_recipients_empty():
    """Test set_to_recipients with an empty data."""
    item = Mock()
    to_recipients = []
    message.set_recipients(item, to_recipients)
    assert item.to == ""


def test_set_to_recipients_invalid():
    """Test set_to_recipients with an invalid data."""
    item = Mock()
    to_recipients = [
        {"emailAddressINVALID": {"addressINVALID": "user2@kopano.com"}},
    ]
    try:
        message.set_recipients(item, to_recipients)
        assert False
    except KeyError:
        assert True


def test_set_user_email():
    """Test set_user_email function."""
    item = Mock()
    message.set_user_email(
        item, "sender", {"emailAddress": {"name": "user1", "address": "user1@kopano.com"}}
    )
    assert item.sender == "user1 <user1@kopano.com>"

    item = Mock()
    message.set_user_email(
        item, "sender", {"emailAddress": {"address": "user1@kopano.com"}}
    )
    assert item.sender == "user1@kopano.com <user1@kopano.com>"


def test_set_subject():
    """Test set_subject function."""
    item = Mock()
    message.update_attr_value(item, "subject", "hello!")
    assert item.subject == "hello!"
