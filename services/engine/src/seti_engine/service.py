"""The stateless HTTP service around the engine (run it with `uvicorn seti_engine.service:app`).

Every request carries the whole game state; nothing is kept between requests, so any number of instances can serve one game (decision D5).
Endpoints: POST /new, POST /apply, POST /legal, POST /project, POST /stats, PUT /archive, PUT /errors, GET /schema, GET /health.
Callers sign their requests (request_auth.py, decision D16); deploy the service private as well (Cloud Run IAM).
See docs/deploy-engine.md.
"""

from __future__ import annotations

import json
import time
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import archive_store, engine, replay, request_auth, stats
from .models import Options
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


class StatsRequest(BaseModel):
    options: Options
    actions: list[dict[str, Any]]
    rng_encoding: str = "exact"  # "double" for a game played before the random state was written as a string (replay.steps)


@app.post("/stats")
def game_stats(req: StatsRequest) -> dict[str, Any]:
    """The statistics of a game that was played to its end (stats.py), from its options and its actions: the engine replays it."""
    file = {
        "format": replay.FORMAT,
        "header": {"options": req.options.model_dump(), "rngEncoding": req.rng_encoding},
        "actions": [{"seq": i, "action": a} for i, a in enumerate(req.actions)],
    }
    return stats.game_stats(file)


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


class ErrorReport(BaseModel):
    source: str  # "worker", "web" or "engine"
    message: str
    detail: Any = None  # the stack, the route, the game id ...


def _clip(value: Any, limit: int) -> Any:
    """Strings are cut so that one report cannot fill the bucket; other values are kept as they are when small."""
    if isinstance(value, str):
        return value[:limit]
    if isinstance(value, dict):
        return {str(k)[:60]: _clip(v, limit) for k, v in list(value.items())[:40]}
    if isinstance(value, list):
        return [_clip(v, limit) for v in value[:40]]
    return value


def save_error(source: str, message: str, detail: Any = None) -> str | None:
    """Write one error report to the bucket (archive_store.py). Never raises: reporting an error must not cause another one."""
    try:
        if not archive_store.valid_source(source):
            source = "unknown"
        body = {
            "source": source,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": message[:2000],
            "detail": _clip(detail, 6000),
        }
        if len(json.dumps(body)) > archive_store.MAX_REPORT_BYTES:
            body["detail"] = None
        path = archive_store.error_path(source)
        archive_store.write(path, body)
        return path
    except Exception:  # noqa: BLE001 - see the docstring
        return None


@app.put("/errors")
def errors(report: ErrorReport) -> JSONResponse:
    """Store one error report of the Worker or the website as an object in the bucket (signed like every request)."""
    path = save_error(report.source, report.message, report.detail)
    if path is None:
        return JSONResponse(status_code=503, content={"error": "report_failed", "message": "the report could not be stored"})
    return JSONResponse(content={"ok": True, "path": path})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    """An unexpected error of the engine itself is stored too; the caller gets a plain 500."""
    save_error("engine", f"{type(exc).__name__}: {exc}", {"route": request.url.path, "trace": traceback.format_exc()})
    return JSONResponse(status_code=500, content={"error": "internal", "message": "internal error"})
