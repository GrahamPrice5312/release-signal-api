from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from html import escape
from typing import Any, Mapping, Protocol


class DeliveryState(str, Enum):
    PENDING = "pending"
    OPENED = "opened"
    BOUNCED = "bounced"


@dataclass(frozen=True)
class BuildEvent:
    project: str
    release_tag: str
    commit_sha: str
    changelog: str


@dataclass(frozen=True)
class ReleaseOperation:
    message_id: str
    release_tag: str
    recipient: str


@dataclass(frozen=True)
class CampaignDiagnostics:
    message_id: str
    state: DeliveryState
    event_count: int
    action: str


class EmailPort(Protocol):
    def send_release(
        self, *, to: str, subject: str, html: str, idempotency_key: str
    ) -> Mapping[str, Any]:
        raise AssertionError("protocol method")

    def list_events(self, message_id: str) -> list[Mapping[str, Any]]:
        raise AssertionError("protocol method")


class ReleaseCampaign:
    def __init__(self, email: EmailPort) -> None:
        self._email = email

    def publish(self, build: BuildEvent, recipient: str) -> ReleaseOperation:
        subject = f"{build.project} {build.release_tag} is ready"
        html = (
            f"<h1>{escape(build.project)} {escape(build.release_tag)}</h1>"
            f"<p>Build <code>{escape(build.commit_sha)}</code> is ready.</p>"
            f"<p>{escape(build.changelog)}</p>"
        )
        stable_input = f"{build.project}:{build.release_tag}:{recipient}"
        idempotency_key = hashlib.sha256(stable_input.encode()).hexdigest()
        result = self._email.send_release(
            to=recipient,
            subject=subject,
            html=html,
            idempotency_key=idempotency_key,
        )
        return ReleaseOperation(
            message_id=str(result["message_id"]),
            release_tag=build.release_tag,
            recipient=recipient,
        )

    def diagnose(self, message_id: str) -> CampaignDiagnostics:
        events = self._email.list_events(message_id)
        kinds = {str(event.get("type", "")).lower() for event in events}
        if "bounce" in kinds or "bounced" in kinds:
            state = DeliveryState.BOUNCED
            action = "remove_recipient_from_next_release"
        elif "open" in kinds or "opened" in kinds:
            state = DeliveryState.OPENED
            action = "keep_recipient_for_next_release"
        else:
            state = DeliveryState.PENDING
            action = "wait_for_delivery_signal"
        return CampaignDiagnostics(message_id, state, len(events), action)
