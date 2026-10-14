"""The stateless HTTP service around the engine (run it with `uvicorn seti_engine.service:app`).

Every request carries the whole game state; nothing is kept between requests, so any number of instances can serve one game (decision D5).
Endpoints: POST /new, POST /apply, POST /legal, POST /project, PUT /archive, GET /schema, GET /health.
Callers sign their requests (request_auth.py, decision D16); deploy the service private as well (Cloud Run IAM).
See docs/deploy-engine.md.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import archive_store, engine, request_auth
from .projection import View, project
from .protocol import (
    PROTOCOL_VERSION,
    ApplyRequest,
    ErrorResponse,
    LegalRequest,
    LegalResponse,
    NewGameRequest,
    ProjectRequest,
    build_schemas,
)

app = FastAPI(title="SETI engine", version=PROTOCOL_VERSION)
_replays = request_auth.ReplayCache()


@app.middleware("http")
async def signed_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Decision D16: every request but /health must be signed by the Worker or the website (see request_auth.py)."""
    if request.url.path != "/health":
        keys = request_auth.trusted_keys()
        if keys is not None:
            try:
                request_auth.verify(
                    request.headers.get("authorization"), request.method, request.url.path, await request.body(), keys, _replays
                )
            except request_auth.Unauthorized as e:
                return JSONResponse(status_code=401, content={"error": "unauthorized", "message": str(e)})
    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "protocol": PROTOCOL_VERSION}


@app.get("/schema")
def schema() -> dict[str, object]:
    return {"protocol": PROTOCOL_VERSION, "schemas": build_schemas()}


@app.post("/new", response_model=engine.StepResult)
def new_game(req: NewGameRequest) -> engine.StepResult:
    return engine.start(req.options)


@app.post("/apply", response_model=engine.StepResult, responses={422: {"model": ErrorResponse}})
def apply(req: ApplyRequest) -> engine.StepResult | JSONResponse:
    try:
        return engine.apply(req.state, req.action)
    except engine.IllegalAction as e:
        body = ErrorResponse(error="illegal_action", message=str(e)[:500], legal=engine.legal_moves(req.state))
        return JSONResponse(status_code=422, content=body.model_dump())


@app.post("/legal", response_model=LegalResponse)
def legal(req: LegalRequest) -> LegalResponse:
    return LegalResponse(legal=engine.legal_moves(req.state))


@app.post("/project", response_model=View)
def project_view(req: ProjectRequest) -> View:
    return project(req.state, req.viewer)


class ArchiveRequest(BaseModel):
    path: str
    body: Any


@app.put("/archive")
def archive(req: ArchiveRequest) -> JSONResponse:
    """Store one file of a game's archive (see archive_store.py). 400 for a path that is not an archive path, 503 when the write failed."""
    if not archive_store.valid_path(req.path):
        return JSONResponse(status_code=400, content={"error": "bad_path", "message": "not an archive path"})
    try:
        archive_store.write(req.path, req.body)
    except archive_store.ArchiveError as e:
        return JSONResponse(status_code=503, content={"error": "archive_failed", "message": str(e)[:300]})
    return JSONResponse(content={"ok": True})
