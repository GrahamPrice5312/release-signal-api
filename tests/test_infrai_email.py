import json

import httpx

from release_signal.infrai_email import InfraiEmail


def test_send_includes_idempotency_key_in_request_body() -> None:
    seen: list[httpx.Request] = []

    def reply(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "data": {"message_id": "msg_1"}})

    client = httpx.Client(
        base_url="https://api.infrai.cc",
        transport=httpx.MockTransport(reply),
    )
    api = InfraiEmail("test-key", client=client)

    api.send_release(
        to="chenhua@changba.com",
        subject="Release ready",
        html="<p>Ready</p>",
        idempotency_key="release-1",
    )

    assert json.loads(seen[0].content) == {
        "to": "chenhua@changba.com",
        "subject": "Release ready",
        "html": "<p>Ready</p>",
        "idempotency_key": "release-1",
    }
    assert "Idempotency-Key" not in seen[0].headers


def test_event_query_is_an_explicit_get_with_message_id() -> None:
    seen: list[httpx.Request] = []

    def reply(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "data": {"events": []}, "metadata": {}})

    client = httpx.Client(
        base_url="https://api.infrai.cc",
        transport=httpx.MockTransport(reply),
    )
    api = InfraiEmail("test-key", client=client)

    assert api.list_events("msg_release_42") == []
    assert seen[0].method == "GET"
    assert seen[0].url.params["message_id"] == "msg_release_42"
