"""Subprocess wrapper around a CLI-based LLM inference runtime.

Per docs/CANON.md: the model runtime is accessed by subprocess for now. LlmBackend is an
abstract interface so an in-process binding can be added later without changing callers
— but that binding is NOT implemented here yet. This package started life wrapping
bitnet.cpp specifically; it now wraps any llama.cpp-family CLI binary (mainline
llama.cpp's `llama-completion`, or bitnet.cpp's fork) via the same `-m -p -n -t --temp`
style flags, plus optional extra one-shot flags (e.g. `-no-cnv`) per model. See
docs/BITNET-POSTMORTEM.md for why the runtime moved off the BitNet fork.
"""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

MOCK_ENV_VAR = "LLM_MOCK"

_MOCK_STRUCTURED_COMPLETION = (
    '{"event": "traffic_incident_suspected", "severity": "high", '
    '"signals": ["sustained_low_speed", "stop_go_index", "eta_slip"], '
    '"eta_impact": 4.0, "corridor": "I-95N", "truck_id": "truck-47"}'
)
_MOCK_NARRATIVE_COMPLETION = (
    "[mock llm completion] Truck 47 has slowed to roughly 35mph in a stop-and-go "
    "pattern on I-95N, and its ETA has slipped about 4 minutes behind plan."
)


class LlmInferenceError(RuntimeError):
    """Raised when the LLM runtime can't be run — missing binary/model, timeout, or a bad exit."""


@dataclass(frozen=True)
class LlmGenerationConfig:
    max_tokens: int = 256
    temperature: float = 0.7
    threads: int = 4
    timeout_seconds: float = 60.0
    extra_args: tuple[str, ...] = field(default_factory=tuple)


class LlmBackend(ABC):
    """How a caller talks to a running LLM, regardless of transport."""

    @abstractmethod
    def generate(self, prompt: str, config: LlmGenerationConfig | None = None) -> str:
        """Run inference and return the generated text (prompt not included)."""
        raise NotImplementedError


class SubprocessLlmBackend(LlmBackend):
    """Shells out to a llama.cpp-family CLI binary (e.g. mainline llama.cpp's
    `llama-completion`, or bitnet.cpp's `main`) per call.

    This is the only real backend implemented today. CPU-only, no GPU flags are ever
    passed. Pass `mock=True` (or set the `LLM_MOCK=1` environment variable) to get
    canned completions without any runtime/model installed at all — useful for
    developing the rest of the pipeline before the Pi/model are set up, and for CI.
    """

    def __init__(
        self,
        binary_path: str | Path | None = None,
        model_path: str | Path | None = None,
        *,
        mock: bool | None = None,
        extra_args: tuple[str, ...] = (),
    ) -> None:
        self._binary_path = Path(binary_path) if binary_path else None
        self._model_path = Path(model_path) if model_path else None
        self._mock = mock if mock is not None else _mock_enabled_via_env()
        # Model-specific one-shot/template flags (e.g. mainline llama.cpp's `-no-cnv`)
        # that every call from this backend instance needs, regardless of which
        # caller built the LlmGenerationConfig for a given generate() call — lets a
        # multi-model comparison harness bind per-model flags once at construction
        # instead of every eval call needing to know about them.
        self._extra_args = extra_args

    def generate(self, prompt: str, config: LlmGenerationConfig | None = None) -> str:
        config = config or LlmGenerationConfig()
        if self._mock:
            return _mock_complete(prompt)

        self._check_binary_and_model_exist()
        command = [
            str(self._binary_path),
            "-m",
            str(self._model_path),
            "-p",
            prompt,
            "-n",
            str(config.max_tokens),
            "-t",
            str(config.threads),
            "--temp",
            str(config.temperature),
            *self._extra_args,
            *config.extra_args,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
                check=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise LlmInferenceError(
                f"LLM runtime did not respond within {config.timeout_seconds}s"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise LlmInferenceError(
                f"LLM runtime exited with status {exc.returncode}: {exc.stderr.strip()}"
            ) from exc
        return result.stdout.strip()

    def _check_binary_and_model_exist(self) -> None:
        if self._binary_path is None or not self._binary_path.exists():
            raise LlmInferenceError(
                f"LLM runtime binary not found at {self._binary_path!r}. Build/install "
                "a llama.cpp-family CLI binary and pass it as binary_path, or construct "
                "with mock=True / set LLM_MOCK=1 to develop without it."
            )
        if self._model_path is None or not self._model_path.exists():
            raise LlmInferenceError(
                f"Model not found at {self._model_path!r}. Point model_path at a GGUF "
                "weights file, or construct with mock=True / set LLM_MOCK=1 to develop "
                "without it."
            )


class InProcessLlmBackend(LlmBackend):
    """Reserved for a future in-process binding (e.g. ctypes/pybind11 around llama.cpp).

    Not implemented yet — see docs/CANON.md. Kept here so callers can be written
    against LlmBackend today and switch transports later without changes.
    """

    def generate(self, prompt: str, config: LlmGenerationConfig | None = None) -> str:
        raise NotImplementedError(
            "In-process LLM binding is reserved for a future session; "
            "use SubprocessLlmBackend for now."
        )


def _mock_enabled_via_env() -> bool:
    return os.environ.get(MOCK_ENV_VAR, "").strip().lower() in {"1", "true", "yes"}


def _mock_complete(prompt: str) -> str:
    if "JSON object" in prompt or '"event"' in prompt:
        return _MOCK_STRUCTURED_COMPLETION
    return _MOCK_NARRATIVE_COMPLETION
