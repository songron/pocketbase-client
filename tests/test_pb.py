import logging
import random

import httpx
import pytest

from pocketbase import Client
from pocketbase.errors import NotFound

ENDPOINT = "https://pocketbase.io/"
EMAIL = "test@example.com"
PASSWORD = "123456"

logging.getLogger("httpx").setLevel(logging.INFO)


@pytest.fixture()
def client():
    client = Client(ENDPOINT, timeout=5.0)
    assert client.authenticated is False
    client.auth_with_password(EMAIL, PASSWORD, coll_name="_superusers")
    assert client.authenticated is True
    yield client


def test_not_authenticated():
    client = Client(ENDPOINT, timeout=5.0)

    with pytest.raises(ValueError):
        client.auth_refresh()

    coll = client.collection("messages")

    with pytest.raises(NotFound):
        coll.get("srmAo0hLxEqYF7F")

    assert coll.get_one({}) is None

    assert len(coll.get_items({})) == 0


def test_timeout(client):
    client = Client(ENDPOINT, timeout=0.01)
    with pytest.raises(httpx.TimeoutException):
        client.collection("messages").get_many({})


def test_auth_refresh(client):
    refreshed_at = client.refreshed_at

    client.auth_refresh()
    assert client.refreshed_at > refreshed_at


def test_get(client):
    coll = client.collection("messages")

    item = coll.get("srmAo0hLxEqYF7F")
    assert item["id"] == "srmAo0hLxEqYF7F"

    with pytest.raises(NotFound):
        coll.get("wrong-id")


def test_get_one(client):
    coll = client.collection("messages")

    item = coll.get_one(
        {
            "fields": "id,message",
            "filter": "message = 'Hello world'",
        }
    )
    assert item is not None
    assert item["message"] == "Hello world"

    assert coll.get_one({"filter": "message = 'this is fake'"}) is None


def test_get_many(client):
    coll = client.collection("messages")

    resp = coll.get_many({"perPage": 2})
    assert len(resp["items"]) == 2
    assert resp["totalItems"] == -1
    assert resp["totalItems"] == -1

    resp = coll.get_many({"perPage": 2, "skipTotal": False})
    assert len(resp["items"]) == 2
    assert resp["totalItems"] > 0
    assert resp["totalItems"] > 0

    resp = coll.get_many({"perPage": 2, "filter": "message = 'Hello world'"})
    assert len(resp["items"]) == 1
    assert resp["items"][0]["message"] == "Hello world"


def test_get_items(client):
    coll = client.collection("messages")

    items = coll.get_items({"perPage": 2})
    assert len(items) == 2


def test_create(client):
    coll = client.collection("messages")

    msg = f"Fake message - {random.random()}"
    item = coll.get_one({"filter": f"message = '{msg}'"})
    assert item is None

    result = coll.create({"message": msg, "author": "eP2jCr1h3NGtsbz"})
    assert result["message"] == msg
    assert coll.get_one({"filter": f"message = '{msg}'"}) is not None
