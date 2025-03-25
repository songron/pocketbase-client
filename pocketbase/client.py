import json
from dataclasses import dataclass
from datetime import UTC, datetime
from json import JSONDecodeError

import httpx

from .collection import Collection
from .errors import ResponseError, NotFound, ValidationNotUnique


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


@dataclass
class User:
    coll_name: str
    user_id: str
    token: str
    refreshed_at: str


class Client:
    def __init__(self, endpoint: str, timeout: float = 10.0):
        self.http_client = httpx.Client(
            base_url=endpoint, timeout=timeout, follow_redirects=True
        )
        self.collection_map: dict[str, Collection] = {}
        self.user = None

    @property
    def authenticated(self) -> bool:
        return self.user is not None

    @property
    def refreshed_at(self) -> str:
        return self.user.refreshed_at if self.user else ""

    def collection(self, id_or_name: str) -> Collection:
        if id_or_name not in self.collection_map:
            self.collection_map[id_or_name] = Collection(id_or_name, self)
        return self.collection_map[id_or_name]

    def _update_user(self, coll_name: str, auth_data: dict):
        user_id = auth_data.get("record", {}).get("id")
        token = auth_data.get("token")
        if not user_id or not token:
            raise ValueError("Invalid authentication")

        self.http_client.headers.update({"Authorization": token})
        self.user = User(
            coll_name=coll_name,
            user_id=user_id,
            token=token,
            refreshed_at=datetime.now(UTC).isoformat(),
        )

    def _auth_with_password(
        self, username_or_email: str, password: str, coll_name: str
    ):
        auth_data = self.request(
            f"/api/collections/{coll_name}/auth-with-password",
            method="POST",
            request_json=dict(
                identity=username_or_email,
                password=password,
            ),
        )
        self._update_user(coll_name, auth_data)

    def auth_with_password(
        self, username_or_email: str, password: str, coll_name: str = "users"
    ):
        self._auth_with_password(username_or_email, password, coll_name)

    def auth_refresh(self) -> bool:
        if self.user is None:
            raise ValueError("Not authenticated")
        assert isinstance(self.user, User), "Invalid user object"

        auth_data = self.request(
            f"/api/collections/{self.user.coll_name}/auth-refresh",
            method="POST",
        )
        self._update_user(self.user.coll_name, auth_data)
        return True

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
