"""FX-04: a tiny client for the synthetic Widget API, with known conformance answers."""

from typing import Any


class MiniClient:
    def __init__(self, session: Any) -> None:
        self.session = session

    def _request(self, method: str, path: str) -> Any:
        return self.session.request(method, path)

    def get_widget(self, widget_id: str) -> Any:
        return self._request("GET", f"/api/v1/widgets/{widget_id}")

    def create_widget(self, body: dict[str, Any]) -> Any:
        return self.session.post("/api/v1/widgets", json=body)

    def list_gadgets(self) -> Any:
        return self.session.get("/api/v1/gadgets")

    def delete_by_parts(self, parts: list[str]) -> Any:
        return self._request("DELETE", "/".join(parts))
