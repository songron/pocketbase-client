import os
import random

import httpx
import pytest
from dotenv import load_dotenv

from pocketbase import Client
from pocketbase.errors import ResponseError, ValidationNotUnique, NotFound

load_dotenv()

pb_endpoint = os.getenv("PB_ENDPOINT", "")
pb_id = os.getenv("PB_ID", "")
pb_pw = os.getenv("PB_PW", "")


@pytest.fixture()
def client():
    yield Client(pb_endpoint)


@pytest.fixture()
def client_timeout():
    yield Client(pb_endpoint, timeout=0.001)


def test_timeout(client_timeout):
    client = client_timeout

    with pytest.raises(httpx.ConnectTimeout):
        client.auth_with_password(pb_id, pb_pw)

    with pytest.raises(httpx.ConnectTimeout):
        client.collection("artist").get_many({})


def test_auth_with_password(client):
    with pytest.raises(ResponseError):
        client.auth_with_password(pb_id, "123")

    assert client.authenticated is False

    client.auth_with_password(pb_id, pb_pw)
    assert client.authenticated is True


@pytest.mark.skip(reason="do not know how to login as admin yet")
def test_auth_as_admin(client):
    email = os.getenv("PB_ADMIN_EMAIL")
    pw = os.getenv("PB_ADMIN_PW")

    with pytest.raises(ResponseError):
        client.auth_as_admin(email, "123")

    assert client.authenticated is False

    client.auth_as_admin(email, pw)
    assert client.authenticated is True


def test_get(client):
    with pytest.raises(NotFound):
        client.collection("artist").get("lxdlvytspput52w")

    client.auth_with_password(pb_id, pb_pw)
    result = client.collection("artist").get("lxdlvytspput52w")
    assert result["id"] == "lxdlvytspput52w"
    assert "name" in result

    result = client.collection("artist").get("lxdlvytspput52w", {"fields": "id"})
    assert result["id"] == "lxdlvytspput52w"
    assert "name" not in result


def test_get_many(client):
    result = client.collection("album").get_many({})
    assert not result.get("items")
    assert result["totalItems"] == -1

    client.auth_with_password(pb_id, pb_pw)
    result = client.collection("album").get_many({})
    assert result.get("items")
    assert result["totalItems"] == -1

    result = client.collection("album").get_many({"skipTotal": 0})
    assert result.get("items")
    assert result["totalItems"] > 0


def test_get_items(client):
    result = client.collection("album").get_items({})
    assert result == []

    client.auth_with_password(pb_id, pb_pw)
    result = client.collection("album").get_items({})
    assert isinstance(result, list)
    assert len(result) > 0


def test_get_one(client):
    assert client.collection("album").get_one({}) is None

    client.auth_with_password(pb_id, pb_pw)
    result = client.collection("album").get_one(
        {
            "fields": "id,title",
            "filter": "title = 'Play'",
        }
    )
    assert isinstance(result, dict)
    assert sorted(result.keys()) == ["id", "title"]
    assert result["title"] == "Play"


def test_create_and_delete(client):
    with pytest.raises(ResponseError):
        client.collection("artist").create({"name": "Bowie"})

    with pytest.raises(NotFound):
        client.collection("artist").delete("iezz48z1g6jaaqv")

    client.auth_with_password(pb_id, pb_pw)
    result = client.collection("artist").create({"name": "Bowie"})
    assert result.get("id")
    assert result["name"] == "Bowie"
    assert client.collection("artist").delete(result["id"]) == {}


def test_create_not_unique(client):
    assert client.authenticated is False
    # This is a problem: it should return the details about uniqueness if not authenticated
    with pytest.raises(ValidationNotUnique):
        client.collection("album").create({"title": "Play"})

    client.auth_with_password(pb_id, pb_pw)

    assert client.collection("album").create_or_ignore({"title": "Play"}) is None

    title = "Play"
    score = random.randint(1, 100)
    result = client.collection("album").create_or_update(
        {"title": title, "score": score},
        f"title = '{title}'",
    )
    assert result["title"] == title
    assert result["score"] == score


def test_update(client):
    with pytest.raises(NotFound):
        client.collection("artist").update("vkvpmbf989iyjkj", {"name": "Bowie2"})

    client.auth_with_password(pb_id, pb_pw)
    name = f"Bowie-{random.randint(1, 9999)}"
    result = client.collection("artist").update("vkvpmbf989iyjkj", {"name": name})
    assert result["name"] == name
