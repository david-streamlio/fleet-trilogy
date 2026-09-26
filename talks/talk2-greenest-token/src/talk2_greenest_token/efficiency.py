"""The efficiency story: pure math, no Pulsar, no I/O.

Per docs/CANON.md, cheap math runs on every truck every tick; the LLM is only
invoked when cheap math flags a probable slowdown (see
`talk1_edge_intelligence.processor.process_event`). So the number of LLM calls a
fleet makes scales with the *flagged-event rate*, not with fleet size directly —
a 200-truck fleet with a 3% incident rate makes roughly the same number of LLM
calls per tick as a 10-truck fleet with a 60% incident rate. That's the whole
point of Tier 1's cheap-math-first design, and it's what this module measures.

This module then attaches a small, clearly-labeled per-call cost/latency/power
model to two named approaches for running that same Tier 1 interpretation step,
so the two can be compared at whatever call volume `count_flagged_events`
produces for a given fleet run:

- ``SMALL_MODEL_CPU``: the approach this project actually ships — a small
  quantized instruct model (Qwen2.5-1.5B/0.5B, Q4_K_M GGUF) run CPU-only via
  mainline llama.cpp, per docs/BITNET-POSTMORTEM.md and docs/CANON.md. Targets
  a Raspberry Pi 4 at the edge, or an ordinary CPU host in the cloud tier.
- ``FULL_PRECISION_GPU``: the traditional alternative — a full-precision model
  requiring a GPU, for the same interpretation workload.

Of the six numbers below, exactly ONE is now real: ``SMALL_MODEL_CPU.latency_s``
is the benchmarked Pi 4 p50 for this exact model
(`eval-results/compare-edge-node00-20260925T030826Z.json`, Qwen2.5-1.5B,
n=110), replacing a prior guess of 0.9s that was never benchmarked and turned
out to be off by ~124x. That correction, on its own, is solid: it doesn't
involve the GPU side at all, and it's real evidence that an unverified
"sounds plausible" latency number can be wrong by two orders of magnitude.

The other five numbers — ``SMALL_MODEL_CPU.power_watts``/``cost_per_call_usd``,
and all three of ``FULL_PRECISION_GPU`` — remain exactly as illustrative and
unverified as they were before this correction. No real GPU benchmark exists
yet (`docs/TALK2-GPU-BENCHMARK-PLAN.md`, blocked, not started), and no real
Pi 4 power draw has ever been measured.

This matters for what can honestly be claimed below. ``cost_factor`` (both
approaches' ``cost_per_call_usd``) is untouched by today's fix and exactly as
illustrative as it always was — it says nothing new. ``energy_factor`` and
``latency_factor`` each now combine one real input with one still-illustrative
one: swapping in the real Pi latency flips the SIGN of the naive per-call
energy comparison (SMALL_MODEL_CPU used to look ~10x greener; now it looks
~12x worse) *given* FULL_PRECISION_GPU's guessed numbers hold — but since
those guesses have never been checked against anything, a real GPU benchmark
could move that "~12x" a long way in either direction, or even flip it back.
The only claim this module can make with real backing is: the illustrative
CPU latency was wrong by ~124x. Everything downstream of the GPU side is
still a labeled assumption, not a finding, and should be presented as one.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from fleet_telemetry_model import TelemetryEvent, is_probable_slowdown

SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class ApproachProfile:
    """A named, per-call cost/latency/power model for one inference approach.

    All three fields are illustrative, labeled assumptions rather than
    benchmark output — EXCEPT ``SMALL_MODEL_CPU.latency_s``, which is real
    (see the module docstring). Check each constant's own comment for which
    of its fields, if any, have been verified before treating a number below
    as more than an assumption:

    - ``latency_s``: wall-clock seconds for one Tier 1 interpretation call
      (cheap math has already run; this is just the LLM's turn).
    - ``power_watts``: sustained power draw of the compute doing that call.
    - ``cost_per_call_usd``: an illustrative amortized dollar cost per call
      (hardware + power, amortized), for the "cost at fleet scale" comparison.
    """

    name: str
    description: str
    latency_s: float
    power_watts: float
    cost_per_call_usd: float


# latency_s is REAL, benchmarked: Qwen2.5-1.5B-Instruct, Q4_K_M GGUF, via
# mainline llama.cpp, CPU-only, on an actual Raspberry Pi 4 — p50=111.51s,
# p95=180.28s, n=110 (eval-results/compare-edge-node00-20260925T030826Z.json).
# This replaces a prior illustrative guess of 0.9s that was never benchmarked
# and turned out to be off by ~124x — that comparison (old guess vs. this real
# number) doesn't involve FULL_PRECISION_GPU at all, so it's solid on its own.
# power_watts and cost_per_call_usd below are still illustrative assumptions —
# no real Pi 4 power draw or amortized-cost measurement has been taken. See
# the module docstring for what is and isn't safe to conclude from combining
# this one real field with FULL_PRECISION_GPU's still-entirely-illustrative
# numbers below.
SMALL_MODEL_CPU = ApproachProfile(
    name="small-model-cpu",
    description="Qwen2.5-1.5B Q4_K_M, mainline llama.cpp, CPU-only, real Pi 4 latency",
    latency_s=111.51,
    power_watts=8.0,
    cost_per_call_usd=0.0002,
)

# Illustrative assumption, ALL THREE fields, unchanged and unverified: a
# full-precision (fp16) model of comparable instruction-following capability,
# served on a GPU. No real GPU benchmark has ever been run for this profile
# (docs/TALK2-GPU-BENCHMARK-PLAN.md, blocked, not started) — latency, power,
# and cost here are all hand-picked guesses, exactly as they were before
# SMALL_MODEL_CPU.latency_s above was corrected. Treat any comparison against
# this profile as conditional on these guesses, not as a real measurement.
FULL_PRECISION_GPU = ApproachProfile(
    name="full-precision-gpu",
    description="full-precision model, GPU-served, same interpretation workload",
    latency_s=0.3,
    power_watts=250.0,
    cost_per_call_usd=0.004,
)

DEFAULT_APPROACHES: tuple[ApproachProfile, ...] = (SMALL_MODEL_CPU, FULL_PRECISION_GPU)


@dataclass(frozen=True)
class ApproachResult:
    """The cost/latency/power of running ``calls`` LLM calls with one approach."""

    approach: str
    description: str
    calls: int
    total_latency_s: float
    total_energy_wh: float
    total_cost_usd: float

    @property
    def avg_latency_s(self) -> float:
        return self.total_latency_s / self.calls if self.calls else 0.0


def count_flagged_events(events: Iterable[TelemetryEvent]) -> int:
    """Count how many events cheap math flagged as a probable slowdown.

    This is the number of LLM calls Tier 1 would make for this batch of
    events — one call per flagged event, never one call per truck per tick.
    """
    return sum(1 for event in events if is_probable_slowdown(event))


def _score_approach(approach: ApproachProfile, calls: int) -> ApproachResult:
    total_latency_s = approach.latency_s * calls
    total_energy_wh = (approach.power_watts * approach.latency_s * calls) / SECONDS_PER_HOUR
    total_cost_usd = approach.cost_per_call_usd * calls
    return ApproachResult(
        approach=approach.name,
        description=approach.description,
        calls=calls,
        total_latency_s=total_latency_s,
        total_energy_wh=total_energy_wh,
        total_cost_usd=total_cost_usd,
    )


def compare_approaches(
    flagged_event_count: int,
    approaches: tuple[ApproachProfile, ...] = DEFAULT_APPROACHES,
) -> dict[str, ApproachResult]:
    """Score every approach against the same number of flagged-event LLM calls.

    Returns a dict keyed by approach name so callers can look up e.g.
    ``result["small-model-cpu"].total_energy_wh``.
    """
    if flagged_event_count < 0:
        raise ValueError("flagged_event_count cannot be negative")
    return {
        approach.name: _score_approach(approach, flagged_event_count) for approach in approaches
    }


def savings_factor(baseline: ApproachResult, contender: ApproachResult) -> dict[str, float]:
    """How many times cheaper/greener `contender` is versus `baseline`, per metric.

    A factor > 1 means `contender` used less of that resource than `baseline`.
    Latency is reported the other way deliberately: a small CPU-only model is
    slower per call than a GPU, so that ratio is expected to be < 1.

    Caution on how much weight each factor can bear, given SMALL_MODEL_CPU's
    latency_s is real but everything about FULL_PRECISION_GPU is still a
    guess (see efficiency.py's module docstring):

    - ``cost_factor`` uses only the two illustrative cost_per_call_usd
      constants — untouched by today's fix, exactly as illustrative as ever.
    - ``latency_factor`` and ``energy_factor`` each divide a real number by
      (or against) FULL_PRECISION_GPU's still-unbenchmarked guess. Computed
      today that's ~372x for latency and ~0.08x for energy — real numbers
      *given* those GPU guesses hold, not numbers a real GPU benchmark is
      guaranteed to reproduce. A real benchmark could move either a long way.

    Whether energy/cost are still the right axes to lead with once the
    latency gap is this large — not just "slower" but plausibly too slow for
    the dispatch decision it's meant to serve — is a fair question for the
    talk to ask directly, independent of how the GPU-side numbers eventually
    resolve.
    """
    return {
        "energy_factor": (
            contender.total_energy_wh and baseline.total_energy_wh / contender.total_energy_wh
        )
        if contender.total_energy_wh
        else float("inf"),
        "cost_factor": (
            baseline.total_cost_usd / contender.total_cost_usd if contender.total_cost_usd else float("inf")
        ),
        "latency_factor": (
            baseline.total_latency_s / contender.total_latency_s
            if contender.total_latency_s
            else float("inf")
        ),
    }
