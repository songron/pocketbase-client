from json import JSONDecodeError
from urllib.parse import urljoin

import httpx
from jvalue import json_extract

from .collection import Collection
from .errors import ResponseError, NotFound, ValidationNotUnique


class Method:
    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"


class Client:

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.authenticated = False
        self.http_client = httpx.Client()
        self.collection_map: dict[str, Collection] = {}

    def collection(self, id_or_name: str) -> Collection:
        if id_or_name not in self.collection_map:
            self.collection_map[id_or_name] = Collection(id_or_name, self)
        return self.collection_map[id_or_name]

    def auth_with_password(self, username_or_email: str, password: str):
        user = self.request(
            "/api/collections/users/auth-with-password",
            method="POST",
            request_json=dict(
                identity=username_or_email,
                password=password,
            ),
        )
        token = user.get("token")
        if not token:
            raise ValueError("Token not found from authentication result")

        self.http_client.headers.update({"Authorization": token})
        self.authenticated = True

    def request(
            self,
            path: str,
            method: str = "GET",
            request_params: dict | None = None,
            request_json: dict | None = None,
    ) -> dict:
        resp = self.http_client.request(
            method,
            urljoin(self.endpoint, path),
            params=request_params,
            json=request_json,
        )

        try:
            resp_json = resp.json()
        except JSONDecodeError:
            resp_json = {}

        if not resp.is_success:
            if resp.status_code == 404:
                error_class = NotFound
            elif json_extract(resp_json, "data.title.code") == "validation_not_unique":
                error_class = ValidationNotUnique
            else:
                error_class = ResponseError
            raise error_class(
                message=resp_json.get("message", ""),
                status_code=resp.status_code,
            )
        return resp_json
