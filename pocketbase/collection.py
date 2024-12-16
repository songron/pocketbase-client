from typing import TYPE_CHECKING
from urllib.parse import quote

from .errors import ValidationNotUnique

if TYPE_CHECKING:
    from .client import Client


class Collection:
    def __init__(self, id_or_name: str, client: "Client"):
        self.id_or_name = id_or_name
        self.client = client
        self.base_path = f"/api/collections/{id_or_name}/records"

    def get(self, id: str, request_params: dict | None = None) -> dict:
        return self.client.request(
            f"{self.base_path}/{quote(id)}",
            method="GET",
            request_params=request_params,
        )

    def get_one(self, request_params: dict) -> dict | None:
        request_params.update({"page": 1, "perPage": 1, "skipTotal": 1})
        data = self.get_many(request_params)
        items = data.get("items") or [None]
        return items[0]

    def get_many(self, request_params: dict) -> dict:
        if "skipTotal" not in request_params:
            request_params["skipTotal"] = 1
        return self.client.request(
            self.base_path,
            method="GET",
            request_params=request_params,
        )

    def get_items(self, request_params: dict) -> list:
        resp = self.get_many(request_params)
        return resp["items"]

    def create(self, request_json: dict) -> dict:
        return self.client.request(
            self.base_path,
            method="POST",
            request_json=request_json,
        )

    def update(self, id: str, request_json: dict) -> dict:
        return self.client.request(
            f"{self.base_path}/{quote(id)}",
            method="PATCH",
            request_json=request_json,
        )

    def delete(self, id: str) -> dict:
        return self.client.request(
            f"{self.base_path}/{quote(id)}",
            method="DELETE",
        )

    def create_or_ignore(self, request_json: dict) -> dict | None:
        try:
            return self.create(request_json)
        except ValidationNotUnique:
            return None

    def create_or_update(self, request_json: dict, unique_filter: str) -> dict:
        record = self.get_one({"filter": unique_filter, "fields": "id"})
        if record is None:
            return self.create(request_json)
        else:
            return self.update(record["id"], request_json)
