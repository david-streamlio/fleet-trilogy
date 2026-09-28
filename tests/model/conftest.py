"""Tier 3 model-eval plumbing: CLI options, real-backend fixture, artifact writing.

Auto-skips the whole tier cleanly when no real llama.cpp-family binary/model is
configured, so `make test` and `make test-integration` are never affected by this
directory.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from llm_inference import SubprocessLlmBackend

from tests.model.eval_lib import FlowBReport, Tier3Report, peak_child_rss_mb
from tests.model.tier2_eval_lib import Tier2Report

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
        "--model-timeout-seconds",
        type=float,
        default=180.0,
        help=(
            "per-call subprocess timeout passed to the LLM backend. LlmGenerationConfig's "
            "own default (60s) is too tight for a full max_tokens completion on a Pi 4 "
            "CPU-only backend at these prompt lengths — hitting it turns format-reliability "
            "and latency measurements into a measurement of the timeout, not the model."
        ),
    )
    group.addoption(
        "--model-threads",
        type=int,
        default=None,
        help=(
            "CPU threads to give each llama-server instance. Defaults to "
            "talk1_edge_intelligence.triage_function.DEFAULT_THREADS (tuned for the M4 "
            "dev machine's 12 performance cores) when unset -- pass this explicitly on "
            "any other host (e.g. a Pi 4 has 4 cores total; 12 threads there means "
            "oversubscription, not more parallelism)."
        ),
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
        "--model-severity-max-mismatch-rate",
        type=float,
        default=0.5,
        help=(
            "maximum acceptable severity-calibration mismatch rate (model's severity "
            "vs. the tier implied by eta_slip_min — see eval_lib.expected_severity). "
            "Deliberately lenient: this is a new, stricter judgment axis than "
            "grounding/format checks, informational for now rather than a gate input."
        ),
    )
    group.addoption(
        "--model-confirm-multiplier",
        type=float,
        default=3.0,
        help=(
            "make compare-models only: models whose gate-1 format_parse_rate clears "
            "--model-format-threshold get a second, bigger severity-calibration-only run "
            "at this multiple of the gate-1 per-tier sample size (gate 2). Fixes the "
            "small-parsed-N problem (e.g. a model with a low parse rate producing too few "
            "parsed cards to trust its severity mismatch rate) without re-running the "
            "cheaper format/grounding/directional axes at higher N too."
        ),
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
    group.addoption(
        "--flow-b-model-ids",
        default=None,
        help=(
            "make compare-flow-b-models only: comma-separated models.toml ids to "
            "re-include for this run even if their `enabled` flag is false (see "
            "models_manifest.load_models_manifest's include_ids). Lets one run widen "
            "or narrow the model set without editing models.toml's durable, "
            "cross-run elimination record."
        ),
    )


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


class _FlowBEvalContext:
    """Minimal stand-in for a Pulsar Functions Context — get_logger() and
    get_user_config_value(key), the only two methods TelemetryCoprocessorFunction
    and LlmTriageFunction call. Configured with the same real binary/model paths
    as the llm_backend fixture, so both functions self-configure exactly as they
    would in production (via user config), not via a backend handed to them
    directly.
    """

    def __init__(self, user_config: dict) -> None:
        self._user_config = user_config
        self._logger = logging.getLogger("flow_b_eval")

    def get_logger(self) -> logging.Logger:
        return self._logger

    def get_user_config_value(self, key: str) -> str | None:
        return self._user_config.get(key)


@pytest.fixture(scope="session")
def flow_b_context(request: pytest.FixtureRequest, llm_backend: SubprocessLlmBackend) -> _FlowBEvalContext:
    # Depending on llm_backend (unused directly — both Flow B functions build
    # their own backend from user config) inherits its skip-when-no-real-model
    # behavior, so this fixture never hands out a context with dead paths.
    binary = _resolve_path(request.config.getoption("--llm-binary"), "LLM_BINARY_PATH")
    model = _resolve_path(request.config.getoption("--llm-model"), "LLM_MODEL_PATH")
    timeout_seconds = request.config.getoption("--model-timeout-seconds")
    threads = request.config.getoption("--model-threads")
    config = {
        "llm_binary_path": binary,
        "llm_model_path": model,
        "timeout_seconds": str(timeout_seconds),
    }
    if threads is not None:
        config["threads"] = str(threads)
    return _FlowBEvalContext(
        config
    )


@pytest.fixture(scope="session")
def flow_b_report(request: pytest.FixtureRequest, llm_backend: SubprocessLlmBackend) -> FlowBReport:
    import platform

    binary = _resolve_path(request.config.getoption("--llm-binary"), "LLM_BINARY_PATH")
    model = _resolve_path(request.config.getoption("--llm-model"), "LLM_MODEL_PATH")
    report = FlowBReport(
        config={
            "binary_path": binary,
            "model_path": model,
            "host": platform.node(),
            "platform": platform.platform(),
            "eval_runs": request.config.getoption("--model-eval-runs"),
        }
    )
    # Stashed separately from _tier3_report so Flow A and Flow B tests running in
    # the same session each get their own artifact instead of one overwriting
    # the other's fields.
    request.config._flow_b_report = report
    return report


@pytest.fixture(scope="session")
def tier2_context(request: pytest.FixtureRequest, llm_backend: SubprocessLlmBackend) -> _FlowBEvalContext:
    # _FlowBEvalContext is a generic get_logger()/get_user_config_value(key) stand-in
    # for a Pulsar Functions Context -- nothing about it is Flow-B-specific, so it's
    # reused as-is here rather than duplicating an identical class under a new name.
    binary = _resolve_path(request.config.getoption("--llm-binary"), "LLM_BINARY_PATH")
    model = _resolve_path(request.config.getoption("--llm-model"), "LLM_MODEL_PATH")
    timeout_seconds = request.config.getoption("--model-timeout-seconds")
    threads = request.config.getoption("--model-threads")
    config = {
        "llm_binary_path": binary,
        "llm_model_path": model,
        "timeout_seconds": str(timeout_seconds),
    }
    if threads is not None:
        config["threads"] = str(threads)
    return _FlowBEvalContext(config)


@pytest.fixture(scope="session")
def tier2_report(request: pytest.FixtureRequest, llm_backend: SubprocessLlmBackend) -> Tier2Report:
    import platform

    binary = _resolve_path(request.config.getoption("--llm-binary"), "LLM_BINARY_PATH")
    model = _resolve_path(request.config.getoption("--llm-model"), "LLM_MODEL_PATH")
    report = Tier2Report(
        config={
            "binary_path": binary,
            "model_path": model,
            "host": platform.node(),
            "platform": platform.platform(),
            "eval_runs": request.config.getoption("--model-eval-runs"),
        }
    )
    request.config._tier2_report = report
    return report


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    EVAL_RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")

    report: Tier3Report | None = getattr(session.config, "_tier3_report", None)
    if report is not None:
        report.resident_ram_mb = peak_child_rss_mb()
        artifact_path = EVAL_RESULTS_DIR / f"tier3-{timestamp}.json"
        artifact_path.write_text(json.dumps(report.to_dict(), indent=2))
        session.config._tier3_summary = report.render_summary(artifact_path)

    flow_b_report: FlowBReport | None = getattr(session.config, "_flow_b_report", None)
    if flow_b_report is not None:
        artifact_path = EVAL_RESULTS_DIR / f"flow-b-{timestamp}.json"
        artifact_path.write_text(json.dumps(flow_b_report.to_dict(), indent=2))
        session.config._flow_b_summary = flow_b_report.render_summary(artifact_path)

    tier2_report: Tier2Report | None = getattr(session.config, "_tier2_report", None)
    if tier2_report is not None:
        artifact_path = EVAL_RESULTS_DIR / f"tier2-{timestamp}.json"
        artifact_path.write_text(json.dumps(tier2_report.to_dict(), indent=2))
        session.config._tier2_summary = tier2_report.render_summary(artifact_path)


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    # pytest_terminal_summary (rather than printing during sessionfinish) is what
    # guarantees this shows up even though pytest captures stdout by default.
    for attr in ("_tier3_summary", "_flow_b_summary", "_tier2_summary"):
        summary = getattr(config, attr, None)
        if summary:
            terminalreporter.write_line(summary)
