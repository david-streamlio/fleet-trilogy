"""Loads models.toml — the Tier 3 model-comparison manifest (see models.toml's own
header comment for the shape). Kept separate from conftest.py/eval_lib.py so both
`make test-model` (single model) and `make compare-models` (all manifest entries)
can share it without a circular import.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "models.toml"


@dataclass(frozen=True)
class ModelEntry:
    id: str
    display_name: str
    binary_path: Path | None
    model_path: Path | None
    extra_args: tuple[str, ...]

    def is_available(self) -> bool:
        return (
            self.binary_path is not None
            and self.model_path is not None
            and self.binary_path.exists()
            and self.model_path.exists()
        )


def _resolve(env_var: str, default_path: str | None) -> Path | None:
    raw = os.environ.get(env_var) or default_path
    return Path(raw).expanduser() if raw else None


def load_models_manifest(manifest_path: Path = DEFAULT_MANIFEST_PATH) -> list[ModelEntry]:
    with manifest_path.open("rb") as f:
        data = tomllib.load(f)
    entries = []
    for raw in data.get("models", []):
        entries.append(
            ModelEntry(
                id=raw["id"],
                display_name=raw.get("display_name", raw["id"]),
                binary_path=_resolve(raw["binary_path_env"], raw.get("default_binary_path")),
                model_path=_resolve(raw["model_path_env"], raw.get("default_model_path")),
                extra_args=tuple(raw.get("extra_args", [])),
            )
        )
    return entries
