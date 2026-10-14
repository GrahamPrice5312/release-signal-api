from typing import Any, Mapping

from release_signal.release_campaign import BuildEvent, DeliveryState, ReleaseCampaign


class RecordingEmail:
    def __init__(self, events: list[Mapping[str, Any]]) -> None:
        self.events = events
        self.sent: dict[str, Any] = {}

    def send_release(self, **request: Any) -> Mapping[str, Any]:
        self.sent = request
        return {"message_id": "msg_release_42"}

    def list_events(self, message_id: str) -> list[Mapping[str, Any]]:
        assert message_id == "msg_release_42"
        return self.events


def test_bounce_wins_when_a_release_was_opened_then_bounced() -> None:
    email = RecordingEmail([{"type": "opened"}, {"type": "bounced"}])
    campaign = ReleaseCampaign(email)
    operation = campaign.publish(
        BuildEvent("FrameForge", "v1.4.0", "8c4f31a", "Faster preview renders."),
        "maker@example.com",
    )

    diagnostics = campaign.diagnose(operation.message_id)

    assert diagnostics.state is DeliveryState.BOUNCED
    assert diagnostics.action == "remove_recipient_from_next_release"
    assert email.sent["to"] == "maker@example.com"
    assert "from" not in email.sent
    assert len(email.sent["idempotency_key"]) == 64
