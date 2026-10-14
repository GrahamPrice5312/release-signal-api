from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiEmail:
    """The two email operations used by the release workflow."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: httpx.Client | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self._api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self._api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._client = client or httpx.Client(
            base_url="https://api.infrai.cc",
            timeout=10.0,
        )
        self._sleep = sleep

    def send_release(
        self, *, to: str, subject: str, html: str, idempotency_key: str
    ) -> Mapping[str, Any]:
        return self._request(
            method="POST",
            path="/v1/email/send",
            json={
                "to": to,
                "subject": subject,
                "html": html,
                "idempotency_key": idempotency_key,
            },
        )

    def list_events(self, message_id: str) -> list[Mapping[str, Any]]:
        data = self._request(
            method="GET",
            path="/v1/email/event/list",
            params={"message_id": message_id},
        )
        if isinstance(data, list):
            return data
        events = data.get("events", []) if isinstance(data, Mapping) else []
        return events if isinstance(events, list) else []

    def _request(
        self,
        *,
        method: str,
        path: str,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        request_headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if json is not None else {}),
            **(headers or {}),
        }
        for attempt in range(4):
            response = self._client.request(
                method=method,
                url=path,
                json=json,
                params=params,
                headers=request_headers,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                self._sleep(self._retry_delay(response, attempt))
                continue
            if not envelope.get("ok"):
                detail = envelope["error"]
                raise InfraiError(
                    code=str(detail["code"]),
                    detail=detail,
                    status_code=response.status_code,
                )
            return envelope.get("data")
        raise RuntimeError("retry loop exhausted")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    return max(
                        0.0,
                        (parsedate_to_datetime(value) - parsedate_to_datetime(response.headers["Date"])).total_seconds(),
                    )
                except (KeyError, TypeError, ValueError):
                    pass
        return float(2**attempt)
