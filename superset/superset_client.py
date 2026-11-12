"""Client tối giản cho Superset REST API (đăng nhập JWT + CSRF)."""
from __future__ import annotations

import json
import os
import time

import requests


class Superset:
    def __init__(self, url: str | None = None, user: str | None = None, password: str | None = None):
        self.url = (url or os.environ.get("SUPERSET_URL", "http://localhost:8088")).rstrip("/")
        self.s = requests.Session()
        user = user or os.environ.get("SUPERSET_ADMIN_USER", "admin")
        password = password or os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
        self._wait_healthy()
        r = self.s.post(f"{self.url}/api/v1/security/login",
                        json={"username": user, "password": password, "provider": "db", "refresh": True})
        r.raise_for_status()
        self.s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        csrf = self.s.get(f"{self.url}/api/v1/security/csrf_token/").json()["result"]
        self.s.headers.update({"X-CSRFToken": csrf, "Referer": self.url})

    def _wait_healthy(self, timeout: int = 300) -> None:
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if self.s.get(f"{self.url}/health", timeout=5).ok:
                    return
            except requests.RequestException:
                pass
            time.sleep(3)
        raise RuntimeError(f"Superset không phản hồi tại {self.url}")

    def _check(self, r: requests.Response) -> dict:
        if not r.ok:
            raise RuntimeError(f"{r.request.method} {r.url} -> {r.status_code}: {r.text[:800]}")
        return r.json() if r.content and "json" in r.headers.get("content-type", "") else {}

    def get(self, path: str, **params) -> dict:
        return self._check(self.s.get(f"{self.url}{path}", params=params))

    def post(self, path: str, payload: dict) -> dict:
        return self._check(self.s.post(f"{self.url}{path}", json=payload))

    def put(self, path: str, payload: dict, **params) -> dict:
        return self._check(self.s.put(f"{self.url}{path}", json=payload, params=params))

    def delete(self, path: str) -> dict:
        return self._check(self.s.delete(f"{self.url}{path}"))

    def list_all(self, resource: str) -> list[dict]:
        out, page = [], 0
        while True:
            q = f"(page:{page},page_size:100)"
            res = self.get(f"/api/v1/{resource}/", q=q)["result"]
            out += res
            if len(res) < 100:
                return out
            page += 1

    @staticmethod
    def dumps(obj) -> str:
        return json.dumps(obj, ensure_ascii=False)
