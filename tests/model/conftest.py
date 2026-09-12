"""Tier 3 model-eval plumbing: CLI options, real-backend fixture, artifact writing.

Auto-skips the whole tier cleanly when no real llama.cpp-family binary/model is
configured, so `make test` and `make test-integration` are never affected by this
directory.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from llm_inference import SubprocessLlmBackend

from tests.model.eval_lib import Tier3Report, peak_child_rss_mb

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_RESULTS_DIR = REPO_ROOT / "eval-results"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("tier3-model-evals")
    group.addoption("--llm-binary", default=None, help="path to the llama.cpp-family CLI binary")
    group.addoption("--llm-model", default=None, help="path to the GGUF model weights")
    group.addoption(
        "--model-eval-runs",
        type=int,
        default=30,
        help="repetitions for the format-reliability and grounding trials",
    )
    group.addoption(
        "--model-format-threshold",
        type=float,
        default=0.8,
        help="minimum acceptable format-reliability rate",
    )
    group.addoption(
        "--model-grounding-max-violation-rate",
        type=float,
        default=0.2,
        help="maximum acceptable grounding-violation rate",
    )
    group.addoption(
        "--model-accuracy-floor",
        type=float,
        default=0.6,
        help="minimum acceptable directional-accuracy F1",
    )
    group.addoption("--model-accuracy-fleet-size", type=int, default=6)
    group.addoption("--model-accuracy-incident-trucks", type=int, default=3)
    group.addoption(
        "--model-accuracy-ticks",
        type=int,
        default=30,
        help=(
            "ticks per simulated truck. The simulator's incident model (see "
            "shared/fleet-simulator/src/fleet_simulator/scenario.py) ramps eta_slip_min "
            "up by 0.6min/tick and needs several ticks of rolling-window history before "
            "stop_go_index crosses is_probable_slowdown's 0.5 threshold — at the old "
            "default of 6, detection never once fired True (confirmed: 36/36 events all "
            "predicted-negative, tp=fp=0), so the eval measured nothing. 30 was chosen by "
            "hand-simulating this exact seed/config and checking flags start around tick "
            "8-10 and produce a real mix of tp/fp/fn/tn by tick 30, well before the "
            "simulator's own incident lifetime (MIN_INCIDENT_TICKS=24) ends."
        ),
    )
    group.addoption("--model-accuracy-seed", type=int, default=1234)


def _resolve_path(cli_value: str | None, env_var: str) -> str | None:
    return cli_value or os.environ.get(env_var)


@pytest.fixture(scope="session")
def llm_backend(request: pytest.FixtureRequest) -> SubprocessLlmBackend:
    binary = _resolve_path(request.config.getoption("--llm-binary"), "LLM_BINARY_PATH")
    model = _resolve_path(request.config.getoption("--llm-model"), "LLM_MODEL_PATH")
    if not binary or not model or not Path(binary).exists() or not Path(model).exists():
        pytest.skip(
            "Tier 3 model evals need a real llama.cpp-family binary + GGUF model. Set "
            "--llm-binary/--llm-model or LLM_BINARY_PATH/LLM_MODEL_PATH env vars. "
            "Skipped, not failed — `make test`/`make test-integration` are unaffected."
        )
    return SubprocessLlmBackend(binary_path=binary, model_path=model, mock=False)


@pytest.fixture(scope="session")
def tier3_report(request: pytest.FixtureRequest, llm_backend: SubprocessLlmBackend) -> Tier3Report:
    import platform

    binary = _resolve_path(request.config.getoption("--llm-binary"), "LLM_BINARY_PATH")
    model = _resolve_path(request.config.getoption("--llm-model"), "LLM_MODEL_PATH")
    report = Tier3Report(
        config={
            "binary_path": binary,
            "model_path": model,
            "host": platform.node(),
            "platform": platform.platform(),
            "eval_runs": request.config.getoption("--model-eval-runs"),
        }
    )
    # Stashed on request.config (not a module global) so pytest_sessionfinish below can
    # find it after tests complete, and so it stays absent — and the artifact is skipped —
    # whenever llm_backend itself was skipped (i.e. no real model is configured).
    request.config._tier3_report = report
    return report


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    report: Tier3Report | None = getattr(session.config, "_tier3_report", None)
    if report is None:
        return
    report.resident_ram_mb = peak_child_rss_mb()
    EVAL_RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = EVAL_RESULTS_DIR / f"tier3-{timestamp}.json"
    artifact_path.write_text(json.dumps(report.to_dict(), indent=2))
    session.config._tier3_summary = report.render_summary(artifact_path)


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    # pytest_terminal_summary (rather than printing during sessionfinish) is what
    # guarantees this shows up even though pytest captures stdout by default.
    summary = getattr(config, "_tier3_summary", None)
    if summary:
        terminalreporter.write_line(summary)
