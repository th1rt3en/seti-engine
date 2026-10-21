"""The service that plays the model's seat in the lobby (Cloudflare Worker -> this service; docs/AI-TURN-BUNDLES.md section 11).

    POST /move    {model, options, actions, seat, plan, rngEncoding?}  ->  {action, plan}
    GET  /models  the versions that can be played
    GET  /health

Requests are signed like those of the engine service (decision D16, `seti_engine.request_auth`): only the Worker may ask. The models are the
approved versions in the folder `SETI_MODELS` (default `models_alpha`); the search can be tuned with `SETI_SEARCH` (a JSON object of `SearchConfig`).
Run: `uvicorn seti_ai.lobby_server:app --port 8090` (needs the extra `lobby`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from seti_engine import request_auth
from seti_engine.models import Options

from .bundle_search import SearchConfig
from .lobby import Lobby, NoSuchModel, NotYourTurn, load_lobby

app = FastAPI(title="SETI AI lobby")
_replays = request_auth.ReplayCache()
_lobby: Lobby | None = None


def lobby() -> Lobby:
    global _lobby
    if _lobby is None:
        config = SearchConfig(**json.loads(os.environ.get("SETI_SEARCH", "{}")))
        _lobby = load_lobby(Path(os.environ.get("SETI_MODELS", "models_alpha")), config, allow_unapproved=os.environ.get("SETI_ALLOW_UNAPPROVED") == "1")
    return _lobby


@app.middleware("http")
async def signed_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
    if request.url.path != "/health":
        keys = request_auth.trusted_keys()
        if keys is not None:
            try:
                request_auth.verify(request.headers.get("authorization"), request.method, request.url.path, await request.body(), keys, _replays)
            except request_auth.Unauthorized as e:
                return JSONResponse(status_code=401, content={"error": "unauthorized", "message": str(e)})
    return await call_next(request)


class MoveRequest(BaseModel):
    model: str
    options: Options
    actions: list[dict[str, Any]]
    seat: int
    plan: list[dict[str, Any]] = []
    rngEncoding: str = "exact"


class MoveResponse(BaseModel):
    action: dict[str, Any]
    plan: list[dict[str, Any]]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models")
def models() -> dict[str, list[str]]:
    return {"models": lobby().models()}


@app.post("/move", response_model=MoveResponse)
def move(req: MoveRequest) -> MoveResponse | JSONResponse:
    try:
        reply = lobby().move(req.model, req.options, req.actions, req.seat, req.plan, req.rngEncoding)
    except NoSuchModel:
        return JSONResponse(status_code=404, content={"error": "no_such_model", "message": f"no approved model {req.model}"})
    except NotYourTurn as e:
        return JSONResponse(status_code=409, content={"error": "not_your_turn", "message": str(e)})
    return MoveResponse(action=reply.action, plan=reply.plan)
