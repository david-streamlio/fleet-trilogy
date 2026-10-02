"""Tier 2 (talk3_pulsar_speaks_english) Tier 3 model evals — see
talk3_pulsar_speaks_english.synthesizer / .prompting. Opt-in, real
llama.cpp-family runtime (see conftest.py's llm_backend/tier2_context fixtures).

Unlike Flow A and the Edge Triage Pipeline, scope and reroute are never model output at all (synthesizer.py
decides both with plain code before the backend is ever invoked) — see
tier2_eval_lib.py's module docstring for what that changes about what "format
reliability" and "grounding" mean for this task.
"""

from __future__ import annotations

import pytest
from llm_inference import LlmServerBackend, SubprocessLlmBackend

from tests.model.tier2_eval_lib import (
    DEFAULT_THREADS,
    TIER2_SCENARIOS,
    check_speakability,
    check_tier2_format_reliability,
    check_tier2_grounding,
    run_tier2_trials,
)

pytestmark = pytest.mark.model


def test_tier2_synthesis_format_speakability_and_grounding(
    request, tier2_context, tier2_report, llm_backend: SubprocessLlmBackend
):
    # llm_backend is depended on only for its skip-when-no-real-model behavior
    # (same convention as edge_triage_context) -- Tier 2's synthesize()/
    # generate_spoken_warning() take a backend directly, no lazy-configure-
    # from-context layer to test the way LlmTriageFunction has, so this builds
    # its own LlmServerBackend from tier2_context's already-resolved paths
    # rather than using llm_backend's SubprocessLlmBackend, for the same
    # per-trial-reload/prompt-cache reasons triage_function.py switched (see
    # docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md).
    total_n = request.config.getoption("--model-eval-runs")
    per_scenario_n = max(1, total_n // 3)
    format_threshold = request.config.getoption("--model-format-threshold")
    max_grounding_violation_rate = request.config.getoption("--model-grounding-max-violation-rate")

    backend = LlmServerBackend(
        binary_path=tier2_context.get_user_config_value("llm_binary_path"),
        model_path=tier2_context.get_user_config_value("llm_model_path"),
        threads=int(tier2_context.get_user_config_value("threads") or DEFAULT_THREADS),
    )
    backend.start()
    try:
        all_trials = []
        grounding_by_scenario = {}
        for name, scenario in TIER2_SCENARIOS.items():
            trials = run_tier2_trials(backend, scenario, per_scenario_n)
            all_trials.extend(trials)
            tier2_report.add_latencies([t.latency_seconds for t in trials])
            grounding_by_scenario[name] = check_tier2_grounding(trials, scenario)
    finally:
        backend.close()

    format_result = check_tier2_format_reliability(all_trials)
    tier2_report.format_reliability = format_result

    speakability_result = check_speakability(all_trials)
    tier2_report.speakability = speakability_result

    tier2_report.grounding_by_scenario = grounding_by_scenario

    # nonempty_rate, not structured_rate, is the real contract here (see
    # tier2_eval_lib's module docstring) -- a model that mostly falls back to
    # clean raw prose is still doing its job; one that fails to produce usable
    # text at all is not.
    assert format_result["nonempty_rate"] >= format_threshold, (
        f"Tier 2 nonempty rate {format_result['nonempty_rate']:.1%} over {format_result['total']} runs "
        f"is below threshold {format_threshold:.1%}; sample errors: {format_result['sample_errors']}"
    )

    assert speakability_result["violation_rate"] <= max_grounding_violation_rate, (
        f"Tier 2 speakability violation rate {speakability_result['violation_rate']:.1%} over "
        f"{speakability_result['total']} cards exceeds bound {max_grounding_violation_rate:.1%}; "
        f"sample violations: {speakability_result['sample_violations']}"
    )

    for name, gr in grounding_by_scenario.items():
        assert gr["violation_rate"] <= max_grounding_violation_rate, (
            f"Tier 2 grounding violation rate for scenario {name!r}: {gr['violation_rate']:.1%} over "
            f"{gr['total']} cards exceeds bound {max_grounding_violation_rate:.1%}; "
            f"sample violations: {gr['sample_violations']}"
        )
