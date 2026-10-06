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

from tests.model.eval_lib import EdgeTriageReport, Tier3Report, peak_child_rss_mb
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
        "--model-backend",
        default="inprocess",
        choices=("inprocess", "server"),
        help=(
            "Edge Triage Pipeline and Tier 2 evals: how the model runs -- `inprocess` "
            "(llama-cpp-python inside the test process, the Functions' default since "
            "2026-10-05) or `server` (llama-server beside it, which every Talk 2 "
            "hardware-spectrum run before that date measured; pass it to reproduce "
            "them). Round 3 always uses llama-server: it calls its HTTP API "
            "(/completion, /apply-template) directly."
        ),
    )
    group.addoption(
        "--model-gpu-layers",
        type=int,
        default=0,
        help=(
            "--model-backend inprocess only: layers to offload to a GPU (default 0, CPU "
            "only; 99 puts the whole model on a Mac's Metal GPU). The server backend "
            "uses whatever its llama.cpp build defaults to."
        ),
    )
    group.addoption(
        "--model-server-args",
        default="",
        help=(
            "--model-backend server only: extra llama-server flags, space-separated. "
            "\"-np 1 --cache-ram 0\" (one slot, no host-RAM prompt cache) makes each call "
            "reuse only the previous call's prompt prefix, like the in-process backend and "
            "like a stream of events that never repeat; without it, --vary-events' recurring "
            "events can be restored from llama-server's cache of earlier prompts."
        ),
    )
    group.addoption(
        "--triage-prompt",
        default="default",
        choices=("default", "event-last"),
        help=(
            "Edge Triage Pipeline evals only: LlmTriageFunction's prompt -- `default` "
            "(DEFAULT_PROMPT_TEMPLATE, every published run) or `event-last` "
            "(EVENT_LAST_PROMPT_TEMPLATE: the same text with the event's fields moved "
            "after the rules, so a different event re-reads ~150 tokens instead of ~400)."
        ),
    )
    group.addoption(
        "--tier2-prompt",
        default="current",
        choices=("current", "published"),
        help=(
            "Tier 2 evals only: the spoken-warning prompt -- `current` "
            "(prompting.SYNTHESIS_WARNING_PROMPT) or `published` "
            "(PUBLISHED_SYNTHESIS_WARNING_PROMPT, without the 2026-10-05 reroute-tense "
            "line), which every Tier 2 measurement before that date used; pass it to "
            "reproduce them."
        ),
    )
    group.addoption(
        "--vary-events",
        action="store_true",
        help=(
            "Edge Triage Pipeline evals only: send a different event on every call "
            "instead of repeating one payload n times. Repeating it lets the backend "
            "serve the whole prompt from its KV cache after the first call, so latency "
            "(and energy per call) measures generation alone -- a lower bound for a "
            "real stream. See eval_lib.run_edge_triage_trials_interleaved."
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
        "--include-model-ids",
        default=None,
        help=(
            "make compare-edge-triage-models / compare-tier2-models only: comma-separated "
            "models.toml ids to "
            "re-include for this run even if their `enabled` flag is false (see "
            "models_manifest.load_models_manifest's include_ids). Lets one run widen "
            "or narrow the model set without editing models.toml's durable, "
            "cross-run elimination record."
        ),
    )
    group.addoption(
        "--only-model-ids",
        default=None,
        help=(
            "make compare-edge-triage-models / compare-tier2-models only: comma-separated "
            "models.toml ids to run EXCLUSIVELY (re-included even if `enabled = false`; "
            "every other entry is skipped; overrides --include-model-ids). For "
            "single-model measurement windows, e.g. docs/TALK2-POWER-MEASUREMENT-PLAN.md."
        ),
    )
    # Round 3 (tests/model/round3_eval.py, test_round3_tasks.py): one model x task x mode per run.
    group.addoption("--round3-server", default=None, help="round 3: path to llama-server")
    group.addoption("--round3-gguf", default=None, help="round 3: path to the model's GGUF")
    group.addoption("--round3-task", default="full", choices=("narrow", "full"), help="round 3: narrow (production) or full (un-narrowed) task")
    group.addoption("--round3-mode", default="raw", choices=("raw", "chat-off", "chat-on", "chat-budget"), help="round 3: raw /completion, or the Qwen chat format with thinking off / on / on with budget forcing")
    group.addoption("--round3-n", type=int, default=2, help="round 3: calls per scenario cell (full: 6 profiles x 3 scenarios; narrow: 3 scenarios x 3n)")
    group.addoption("--round3-think-budget", type=int, default=2048, help="round 3: chat-on token budget for reasoning, on top of the card's 300")
    group.addoption("--round3-temperature", type=float, default=0.2, help="round 3: production's DEFAULT_TEMPERATURE, the same in every mode")
    group.addoption("--round3-variant", default="base", help="round 3 ablation (test_round3_ablation.py): base|facts|tables|template|examples|temp0|grammar")


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


class _EdgeTriageEvalContext:
    """Minimal stand-in for a Pulsar Functions Context — get_logger() and
    get_user_config_value(key), the only two methods TelemetryCoprocessorFunction
    and LlmTriageFunction call. Configured with the same real binary/model paths
    as the llm_backend fixture, so both functions self-configure exactly as they
    would in production (via user config), not via a backend handed to them
    directly.
    """

    def __init__(self, user_config: dict) -> None:
        self._user_config = user_config
        self._logger = logging.getLogger("edge_triage_eval")

    def get_logger(self) -> logging.Logger:
        return self._logger

    def get_user_config_value(self, key: str) -> str | None:
        return self._user_config.get(key)


@pytest.fixture(scope="session")
def edge_triage_context(request: pytest.FixtureRequest, llm_backend: SubprocessLlmBackend) -> _EdgeTriageEvalContext:
    # Depending on llm_backend (unused directly — both Edge Triage Pipeline functions build
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
        "llm_backend": request.config.getoption("--model-backend"),
        "llm_gpu_layers": str(request.config.getoption("--model-gpu-layers")),
        "prompt_template": triage_prompt_template(request.config.getoption("--triage-prompt")),
        "llm_extra_args": request.config.getoption("--model-server-args"),
    }
    if threads is not None:
        config["threads"] = str(threads)
    return _EdgeTriageEvalContext(
        config
    )


def triage_prompt_template(name: str) -> str:
    """--triage-prompt's value -> the LlmTriageFunction template it names."""
    from talk1_edge_intelligence.triage_function import (
        DEFAULT_PROMPT_TEMPLATE,
        EVENT_LAST_PROMPT_TEMPLATE,
    )

    return {"default": DEFAULT_PROMPT_TEMPLATE, "event-last": EVENT_LAST_PROMPT_TEMPLATE}[name]


@pytest.fixture(scope="session")
def edge_triage_report(request: pytest.FixtureRequest, llm_backend: SubprocessLlmBackend) -> EdgeTriageReport:
    import platform

    binary = _resolve_path(request.config.getoption("--llm-binary"), "LLM_BINARY_PATH")
    model = _resolve_path(request.config.getoption("--llm-model"), "LLM_MODEL_PATH")
    report = EdgeTriageReport(
        config={
            "binary_path": binary,
            "model_path": model,
            "host": platform.node(),
            "platform": platform.platform(),
            "eval_runs": request.config.getoption("--model-eval-runs"),
        }
    )
    # Stashed separately from _tier3_report so Flow A and Edge Triage Pipeline tests running in
    # the same session each get their own artifact instead of one overwriting
    # the other's fields.
    request.config._edge_triage_report = report
    return report


@pytest.fixture(scope="session")
def tier2_context(request: pytest.FixtureRequest, llm_backend: SubprocessLlmBackend) -> _EdgeTriageEvalContext:
    # _EdgeTriageEvalContext is a generic get_logger()/get_user_config_value(key) stand-in
    # for a Pulsar Functions Context -- nothing about it is specific to the Edge Triage Pipeline, so it's
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
    return _EdgeTriageEvalContext(config)


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

    edge_triage_report: EdgeTriageReport | None = getattr(session.config, "_edge_triage_report", None)
    if edge_triage_report is not None:
        artifact_path = EVAL_RESULTS_DIR / f"edge-triage-{timestamp}.json"
        artifact_path.write_text(json.dumps(edge_triage_report.to_dict(), indent=2))
        session.config._edge_triage_summary = edge_triage_report.render_summary(artifact_path)

    tier2_report: Tier2Report | None = getattr(session.config, "_tier2_report", None)
    if tier2_report is not None:
        artifact_path = EVAL_RESULTS_DIR / f"tier2-{timestamp}.json"
        artifact_path.write_text(json.dumps(tier2_report.to_dict(), indent=2))
        session.config._tier2_summary = tier2_report.render_summary(artifact_path)


def pytest_terminal_summary(terminalreporter, exitstatus: int, config: pytest.Config) -> None:
    # pytest_terminal_summary (rather than printing during sessionfinish) is what
    # guarantees this shows up even though pytest captures stdout by default.
    for attr in ("_tier3_summary", "_edge_triage_summary", "_tier2_summary"):
        summary = getattr(config, attr, None)
        if summary:
            terminalreporter.write_line(summary)
