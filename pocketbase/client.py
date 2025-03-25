import json
import time
from json import JSONDecodeError

import httpx

from .collection import Collection
from .errors import ResponseError, NotFound, ValidationNotUnique

DEFAULT_AUTH_DURATION = 86400.0


class Method:
    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"


def validation_not_unique(resp_json: dict) -> bool:
    data = resp_json.get("data")
    if not isinstance(data, dict):
        return False
    for _, v in data.items():
        if isinstance(v, dict) and v.get("code") == "validation_not_unique":
            return True
    return False


class Client:
    def __init__(self, endpoint: str, timeout: float = 10.0):
        self.http_client = httpx.Client(
            base_url=endpoint, timeout=timeout, follow_redirects=True
        )
        self.collection_map: dict[str, Collection] = {}
        self.auth_data = {}

    def _update_auth(self, auth_data: dict, auth_duration: float):
        token = auth_data.get("token")
        if not token:
            raise ValueError("Invalid authentication")

        self.http_client.headers.update({"Authorization": token})

        auth_data["refreshed_at"] = time.time() - 60.0
        auth_data["auth_duration"] = auth_duration
        self.auth_data = auth_data

    @property
    def authenticated(self) -> bool:
        return bool(self.auth_data.get("token"))

    @property
    def refreshed_at(self) -> float:
        return self.auth_data.get("refreshed_at", 0.0)

    @property
    def auth_duration(self) -> float:
        return self.auth_data.get("auth_duration", DEFAULT_AUTH_DURATION)

    @property
    def auth_expired(self) -> bool:
        return time.time() - self.refreshed_at >= self.auth_duration

    def collection(self, id_or_name: str) -> Collection:
        if id_or_name not in self.collection_map:
            self.collection_map[id_or_name] = Collection(id_or_name, self)
        return self.collection_map[id_or_name]

    def auth_with_password(
        self,
        username_or_email: str,
        password: str,
        coll_name: str = "users",
        auth_duration: float = DEFAULT_AUTH_DURATION,
    ):
        auth_data = self.request(
            f"/api/collections/{coll_name}/auth-with-password",
            method="POST",
            request_json=dict(
                identity=username_or_email,
                password=password,
            ),
        )
        self._update_auth(auth_data, auth_duration)

    def auth_refresh(self):
        if not self.authenticated:
            raise ValueError("Not authenticated")

        coll_name = self.auth_data.get("record", {}).get("collectionName", "users")
        auth_data = self.request(
            f"/api/collections/{coll_name}/auth-refresh",
            method="POST",
        )
        self._update_auth(auth_data, self.auth_duration)

    def request(
        self,
        path: str,
        method: str = "GET",
        request_params: dict | None = None,
        request_json: dict | None = None,
    ) -> dict:
        resp = self.http_client.request(
            method,
            url=path,
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
            elif validation_not_unique(resp_json):
                error_class = ValidationNotUnique
            else:
                error_class = ResponseError
            raise error_class(
                message=json.dumps(resp_json),
                status_code=resp.status_code,
            )
        return resp_json
