"""JSON (de)serialization helpers shared by every talk that reads/writes these models."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def to_json(model: BaseModel) -> str:
    """Serialize a model to its wire JSON, using field aliases (e.g. `_ground_truth`)."""
    return model.model_dump_json(by_alias=True)


def from_json(model_cls: type[ModelT], data: str | bytes) -> ModelT:
    """Parse wire JSON into a model instance."""
    return model_cls.model_validate_json(data)


def strip_ground_truth(payload: dict) -> dict:
    """Remove the simulator-only `_ground_truth` label from a decoded event payload.

    Call this before handing telemetry to anything that's meant to be doing real
    inference — the label exists for scoring the simulator, not for the model to see.
    """
    return {key: value for key, value in payload.items() if key != "_ground_truth"}
