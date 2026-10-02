"""Fast, offline unit tests for models_manifest.load_models_manifest's id filters --
no real model needed. Locks in `only_ids` semantics the power-measurement plan
(docs/TALK2-POWER-MEASUREMENT-PLAN.md) depends on: exactly one model per meter
window, and a typo'd id failing loudly instead of silently running the wrong set.
"""

from __future__ import annotations

import pytest

from tests.model.models_manifest import load_models_manifest, parse_model_ids

_MANIFEST = """
[[models]]
id = "enabled-a"
binary_path_env = "UNSET_BIN_A"
model_path_env = "UNSET_MODEL_A"

[[models]]
id = "enabled-b"
binary_path_env = "UNSET_BIN_B"
model_path_env = "UNSET_MODEL_B"

[[models]]
id = "disabled-c"
enabled = false
binary_path_env = "UNSET_BIN_C"
model_path_env = "UNSET_MODEL_C"
"""


@pytest.fixture
def manifest_path(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(_MANIFEST)
    return path


def _ids(entries):
    return [e.id for e in entries]


def test_default_skips_disabled(manifest_path):
    assert _ids(load_models_manifest(manifest_path)) == ["enabled-a", "enabled-b"]


def test_include_ids_widens(manifest_path):
    entries = load_models_manifest(manifest_path, include_ids=frozenset({"disabled-c"}))
    assert _ids(entries) == ["enabled-a", "enabled-b", "disabled-c"]


def test_only_ids_narrows_to_exactly_those(manifest_path):
    assert _ids(load_models_manifest(manifest_path, only_ids=frozenset({"enabled-b"}))) == ["enabled-b"]


def test_only_ids_reincludes_disabled(manifest_path):
    assert _ids(load_models_manifest(manifest_path, only_ids=frozenset({"disabled-c"}))) == ["disabled-c"]


def test_only_ids_overrides_include_ids(manifest_path):
    entries = load_models_manifest(
        manifest_path, include_ids=frozenset({"disabled-c"}), only_ids=frozenset({"enabled-a"})
    )
    assert _ids(entries) == ["enabled-a"]


def test_only_ids_unknown_id_raises(manifest_path):
    with pytest.raises(ValueError, match="enabled-z"):
        load_models_manifest(manifest_path, only_ids=frozenset({"enabled-a", "enabled-z"}))


def test_parse_model_ids():
    assert parse_model_ids(None) is None
    assert parse_model_ids("") is None
    assert parse_model_ids(" a, b ,,") == frozenset({"a", "b"})
