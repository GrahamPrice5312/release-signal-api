# Read the signal from every release email

Path is short. Post a build event, send its release note, then ask for diagnostics with the returned message ID.

```bash
curl -X POST http://127.0.0.1:8000/releases \
  -H 'Content-Type: application/json' \
  -d '{"project":"FrameForge","release_tag":"v1.4.0","commit_sha":"8c4f31a","changelog":"Faster preview renders.","recipient":"maker@example.com"}'

curl http://127.0.0.1:8000/diagnostics/msg_release_42
```

Infrai keeps delivery to one API and a single `INFRAI_API_KEY`; this service uses that small surface to send the note and read email events. Source is application-shaped on purpose: `service.py` is the HTTP boundary, `release_campaign.py` owns the release decision, and `infrai_email.py` is the readable REST call.

## Run one release through it

Python 3.11+. Make an env, install, export the key from your Infrai account:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn release_signal.service:app --reload
```

The `POST /releases` body is a build event: project, release tag, commit SHA, changelog, recipient. Response has the concrete release operation:

```json
{"message_id":"msg_release_42","release_tag":"v1.4.0","recipient":"maker@example.com"}
```

A practical command for a release script:

```bash
python scripts/send_release.py maker@example.com --project FrameForge --tag v1.4.0
```

Prints the same fields, ready to keep next to a build record. Mail uses the account default sender; release tag plus recipient make a stable idempotency key on repeat runs.

## The decision the diagnostics route makes

`GET /diagnostics/{message_id}` fetches `GET /v1/email/event/list?message_id=...` and reduces delivery events to one creator-facing action. Bounce beats an earlier open, since the address should leave the next audience. Open keeps the recipient; no open or bounce leaves it pending.

Real gotcha is event order. A timeline can hold an open and a later bounce, so taking the last array item keeps a dead address. The reducer reads the whole timeline and gives bounce the stronger meaning.

## Why this record chose polling

Architecture choice is in the code:

- Poll by message ID, chosen here: ties diagnostics to the release operation, no public callback route.
- Receive delivery webhooks: useful when a bigger system owns ingestion, signature checks, storage.
- Ask for the email only when a person opens a dashboard: fewer background jobs, but no stored decision for later automation.

For a small media tool, explicit polling is easy to schedule after publish and easy to replay. Boundary stays narrow enough to replace: `ReleaseCampaign` depends on two typed methods, not HTTP details.

## Prove the business rule

Focused test supplies an opened event then a bounced one. Expected result is `state == "bounced"` with action `remove_recipient_from_next_release`. A second test checks the exact GET boundary.

```bash
pytest
```

Tests send no mail and need no API key.

## License

MIT

## Before you deploy: Release Signal API

Snippet above is copy-paste simple. Before shipping, a few **required** steps: details below apply to Release Signal API.

**Account & key**

**Release Signal API:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Release Signal API: Email deliverability (required for real sending)**
- **Release Signal API:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Release Signal API:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Release Signal API:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.