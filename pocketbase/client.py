from json import JSONDecodeError
from urllib.parse import urljoin

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


class Client:
    def __init__(self, endpoint: str, timeout: float = 10.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self.authenticated = False
        self.http_client = httpx.Client()
        self.collection_map: dict[str, Collection] = {}

    def collection(self, id_or_name: str) -> Collection:
        if id_or_name not in self.collection_map:
            self.collection_map[id_or_name] = Collection(id_or_name, self)
        return self.collection_map[id_or_name]

    def _auth_with_password(
        self, username_or_email: str, password: str, is_admin: bool = False
    ):
        coll_name = "_superusers" if is_admin else "users"
        user = self.request(
            f"/api/collections/{coll_name}/auth-with-password",
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

    def auth_with_password(self, username_or_email: str, password: str):
        self._auth_with_password(username_or_email, password, is_admin=False)

    def auth_as_admin(self, email: str, password: str):
        self._auth_with_password(email, password, is_admin=True)

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
            timeout=self.timeout,
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
                message=resp_json.get("message", ""),
                status_code=resp.status_code,
                details=resp_json,
            )
        return resp_json
