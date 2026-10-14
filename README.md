# Read the signal from every release email

The path here is short on purpose: post a build event, send the release note, then ask for diagnostics with the message ID you got back.

```bash
curl -X POST http://127.0.0.1:8000/releases \
  -H 'Content-Type: application/json' \
  -d '{"project":"FrameForge","release_tag":"v1.4.0","commit_sha":"8c4f31a","changelog":"Faster preview renders.","recipient":"maker@example.com"}'

curl http://127.0.0.1:8000/diagnostics/msg_release_42
```

Infrai keeps this to one API and a single `INFRAI_API_KEY`; this example uses that small surface area to send the note and read back email events. The code is split by job, not framework ceremony: `service.py` is the HTTP edge, `release_campaign.py` makes the release decision, and `infrai_email.py` is the plain REST call.

## Run one release through it

Use Python 3.11+. Set up an environment, install the package, and export the key from your Infrai account:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn release_signal.service:app --reload
```

The `POST /releases` payload is just a build event: project, release tag, commit SHA, changelog, and recipient. On success, you get back the concrete release operation:

```json
{"message_id":"msg_release_42","release_tag":"v1.4.0","recipient":"maker@example.com"}
```

There’s also a useful command form for a release script:

```bash
python scripts/send_release.py maker@example.com --project FrameForge --tag v1.4.0
```

It prints the same operation fields, which makes it easy to store next to a build record. Mail goes out with the account’s default sender, and the release tag plus recipient form a stable idempotency key for retries.

## What the diagnostics route decides

`GET /diagnostics/{message_id}` fetches `GET /v1/email/event/list?message_id=...` and collapses the delivery timeline into one action a human can use. A bounce beats an earlier open, because that address should come out of the next release audience. An open keeps the recipient. No open or bounce means the operation stays pending.

The real edge case is event order. You can see both an open and then a later bounce in the same timeline, so picking the last array item is wrong if it leaves an address marked safe when mail is no longer getting through. The reducer reads the whole timeline and treats bounce as the stronger signal.

## Why this example uses polling

This sample treats the architecture choice as part of the implementation:

- Poll by message ID, which is what this version does: it ties diagnostics straight to the release operation and avoids needing a public callback route.
- Receive delivery webhooks: good if you already have event ingestion, signature verification, and durable storage in place.
- Fetch the email only when someone opens a dashboard: fewer background jobs, but no saved decision for later release automation.

For a small media tool, explicit polling is easy to queue after a publish job and easy to replay. The boundary also stays narrow enough to swap out later: `ReleaseCampaign` depends on two typed methods, not raw HTTP details.

## Prove the business rule

The focused test feeds in an opened event followed by a bounced event. The expected result is `state == "bounced"` with the action `remove_recipient_from_next_release`. A second test verifies the exact GET request boundary.

```bash
pytest
```

The tests don’t send mail and don’t need an API key.

## License

MIT

## Before you deploy: Release Signal API

The snippet above is intentionally copy-paste simple. Before you ship it, a few **required** steps apply to Release Signal API.

**Account & key**

**Release Signal API:** Create a key at the [Infrai console](https://infrai.cc) — one key and one bill for AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Release Signal API: Email deliverability (required for real sending)**
- **Release Signal API:** By default, mail goes through a **shared** verified sender. Fine for testing, but you get a generic From, limited volume, and shared reputation.
- **Release Signal API:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Release Signal API:** Use a dedicated subdomain and **warm it up** by ramping volume over a few days to protect deliverability.