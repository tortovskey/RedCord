from __future__ import annotations

import json
import urllib.error
import urllib.request


class SyncError(RuntimeError):
    pass


class SyncClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request_code(self, email: str) -> str:
        data = self._post("/auth/request-code", {"email": email})
        return str(data.get("message", "Code requested"))

    def verify_code(self, email: str, code: str) -> str:
        data = self._post("/auth/verify-code", {"email": email, "code": code})
        token = str(data.get("token", ""))
        if not token:
            raise SyncError("Backend did not return token.")
        return token

    def status(self, token: str) -> dict[str, object]:
        return self._post("/sync/status", {}, token=token)

    def push(self, payload: dict[str, object], token: str) -> dict[str, object]:
        return self._post("/sync/push", payload, token=token)

    def pull(self, since: str, token: str) -> dict[str, object]:
        return self._post("/sync/pull", {"since": since}, token=token)

    def _post(self, path: str, payload: dict[str, object], token: str = "") -> dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise SyncError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise SyncError(f"Sync backend unavailable: {exc.reason}") from exc
