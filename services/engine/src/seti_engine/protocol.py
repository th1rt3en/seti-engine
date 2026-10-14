"""The wire protocol of the engine service: request and response models and the JSON Schema generated from them (decision D11).

`PROTOCOL_VERSION` changes whenever the generated schema changes. A test compares the committed schema in packages/protocol with the
models, so the two cannot drift apart. Actions are opaque objects: the client only sends back one of the `legal` moves it was given.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .engine import StepResult
from .models import GameState, Options
from .projection import View

PROTOCOL_VERSION = "0.1.0"

Action = dict[str, Any]


class NewGameRequest(BaseModel):
    options: Options


class ApplyRequest(BaseModel):
    state: GameState
    action: Action = Field(description="One of the `legal` moves returned with the state; an object with a `type`.")


class LegalRequest(BaseModel):
    state: GameState


class ProjectRequest(BaseModel):
    state: GameState
    viewer: int | None = Field(default=None, description="The player index, or null for a spectator.")


class LegalResponse(BaseModel):
    legal: list[Action]


class ErrorResponse(BaseModel):
    error: str
    message: str
    legal: list[Action] = Field(default_factory=list)


MODELS: dict[str, type[BaseModel]] = {
    "Options": Options,
    "GameState": GameState,
    "StepResult": StepResult,
    "View": View,
    "NewGameRequest": NewGameRequest,
    "ApplyRequest": ApplyRequest,
    "LegalRequest": LegalRequest,
    "ProjectRequest": ProjectRequest,
    "LegalResponse": LegalResponse,
    "ErrorResponse": ErrorResponse,
}


# Options is what a client writes (the defaults make fields optional); everything else is what the service sends, so every field is present.
INPUT_MODELS = ("Options", "NewGameRequest")


def build_schemas() -> dict[str, dict[str, Any]]:
    """One JSON Schema document per model, with its definitions under $defs. Inputs come last so their definitions win when merged."""
    names = [n for n in MODELS if n not in INPUT_MODELS] + [n for n in MODELS if n in INPUT_MODELS]
    return {n: MODELS[n].model_json_schema(mode="validation" if n in INPUT_MODELS else "serialization") for n in names}
