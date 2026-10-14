from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from .infrai_email import InfraiEmail, InfraiError
from .release_campaign import BuildEvent, ReleaseCampaign


class ReleaseRequest(BaseModel):
    project: str = Field(min_length=1)
    release_tag: str = Field(min_length=1)
    commit_sha: str = Field(min_length=7)
    changelog: str = Field(min_length=1)
    recipient: EmailStr


class ReleaseResponse(BaseModel):
    message_id: str
    release_tag: str
    recipient: str


class DiagnosticsResponse(BaseModel):
    message_id: str
    state: str
    event_count: int
    action: str


app = FastAPI(title="Release Signal")


def campaign() -> ReleaseCampaign:
    return ReleaseCampaign(InfraiEmail())


def public_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": error.code, "detail": error.detail})


@app.post("/releases", response_model=ReleaseResponse, status_code=201)
def publish_release(request: ReleaseRequest) -> ReleaseResponse:
    try:
        result = campaign().publish(
            BuildEvent(
                project=request.project,
                release_tag=request.release_tag,
                commit_sha=request.commit_sha,
                changelog=request.changelog,
            ),
            str(request.recipient),
        )
        return ReleaseResponse(**asdict(result))
    except InfraiError as error:
        raise public_error(error) from error


@app.get("/diagnostics/{message_id}", response_model=DiagnosticsResponse)
def release_diagnostics(message_id: str) -> DiagnosticsResponse:
    try:
        result = campaign().diagnose(message_id)
        return DiagnosticsResponse(**asdict(result))
    except InfraiError as error:
        raise public_error(error) from error
