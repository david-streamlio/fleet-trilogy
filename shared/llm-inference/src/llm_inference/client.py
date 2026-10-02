"""LLM inference backends, behind a common LlmBackend interface.

Per docs/CANON.md: the on-stage model runtime (edge/cloud tiers) is accessed by
subprocess. LlmBackend is an abstract interface so other transports can be added
without changing callers. SubprocessLlmBackend wraps any llama.cpp-family CLI
binary (mainline llama.cpp's `llama-completion`, or bitnet.cpp's fork) via the same
`-m -p -n -t --temp` style flags, plus optional extra one-shot flags (e.g.
`-no-cnv`) per model — see docs/BITNET-POSTMORTEM.md for why the runtime moved off
the BitNet fork. HttpLlmBackend is a client for a model an existing
OpenAI-chat-completions-compatible server already hosts (e.g. an eval run against
a homelab vllm-mlx/LiteLLM engine) — it's a client, not a process owner, and is not
part of the on-stage tiers. LlmServerBackend, like HttpLlmBackend, talks to a
server over HTTP, but — like SubprocessLlmBackend — owns that server's process
lifecycle itself (starts llama-server, waits for it to become healthy, shuts it
down); see its own docstring for why this exists (SubprocessLlmBackend reloads the
whole model from scratch on every single generate() call, measured as the dominant
cost for any workload that calls it many times against the same model).
InProcessLlmBackend remains reserved/unimplemented.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

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
    # Structured fields for the two per-call concepts every backend needs to be able
    # to express (grammar-constrained decoding, stop sequences) — first-class rather
    # than left inside extra_args, so a caller can build one LlmGenerationConfig and
    # get correct behavior from ANY backend (SubprocessLlmBackend translates these
    # into --grammar/--reverse-prompt CLI flags; LlmServerBackend into JSON body
    # fields). A caller that only sets these via extra_args would silently get no
    # grammar constraint at all under a backend that doesn't parse raw CLI flags.
    grammar: str | None = None
    stop: tuple[str, ...] = field(default_factory=tuple)
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
        self._binary_path = Path(binary_path).expanduser() if binary_path else None
        self._model_path = Path(model_path).expanduser() if model_path else None
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
        ]
        if config.grammar:
            command += ["--grammar", config.grammar]
        for stop_word in config.stop:
            command += ["--reverse-prompt", stop_word]
        command += [*self._extra_args, *config.extra_args]
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


class HttpLlmBackend(LlmBackend):
    """Client for a model an existing OpenAI-chat-completions-compatible server is
    already hosting (e.g. a vllm-mlx engine behind a LiteLLM proxy), rather than a
    llama.cpp-family binary this project starts/stops itself.

    Unlike SubprocessLlmBackend, this backend never owns the model's process
    lifecycle — someone else's server is already up. `LlmGenerationConfig.threads`
    and `.extra_args` are subprocess/CLI-flag concepts and are ignored here.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        mock: bool | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._mock = mock if mock is not None else _mock_enabled_via_env()

    def generate(self, prompt: str, config: LlmGenerationConfig | None = None) -> str:
        config = config or LlmGenerationConfig()
        if self._mock:
            return _mock_complete(prompt)

        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions", data=payload, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LlmInferenceError(f"LLM server returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LlmInferenceError(
                f"could not reach LLM server at {self._base_url}: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise LlmInferenceError(
                f"LLM server did not respond within {config.timeout_seconds}s"
            ) from exc

        try:
            return body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise LlmInferenceError(f"unexpected response shape from LLM server: {body!r}") from exc


class LlmServerBackend(LlmBackend):
    """Starts a llama.cpp-family HTTP server (mainline llama.cpp's `llama-server`)
    once and keeps it running across many generate() calls, instead of
    SubprocessLlmBackend's one-process-per-call model.

    Fixes two real, measured problems with SubprocessLlmBackend for any workload
    that calls generate() many times against the same model — an eval harness's
    dozens-to-hundreds of trials per model, or a long-running Pulsar Function
    processing many events:

    1. SubprocessLlmBackend reloads the model's full weights and reinitializes the
       GPU backend (Metal, on this repo's dev machine — confirmed via `lsof`
       showing the Metal shader library get re-mapped on every single subprocess
       launch) from scratch on EVERY call. For anything bigger than a couple
       hundred MB this dominates wall time; measured directly during a 14-model
       Edge Triage Pipeline comparison run that was taking far longer than the model spectrum
       alone would predict.
    2. SubprocessLlmBackend's file-based prompt cache (`--prompt-cache`/
       `--prompt-cache-ro`) needs something to have WRITTEN that file first —
       `-ro` never writes it, and nothing in this pipeline ever ran a non-`-ro`
       pass, so the cache file never existed and every call reprocessed the full
       prompt from scratch. llama-server's internal request-slot cache reuses a
       shared prompt prefix across HTTP requests automatically, with no extra
       code: verified live against a real model, a second call sharing an 86/90
       token prefix with the first dropped prompt-processing time from 44ms to
       3.6ms.

    Uses llama-server's raw `/completion` endpoint, not the OpenAI-compatible
    `/v1/chat/completions` one HttpLlmBackend uses — specifically because
    `/completion` sends the prompt exactly as given, with no chat-template
    wrapping, matching SubprocessLlmBackend's `-no-cnv` one-shot behavior
    byte-for-byte (verified live: the server's own echoed `prompt` field showed
    only a BOS token added, nothing else). Switching to the chat-completions
    endpoint would silently change what the model actually sees — a measurement
    bug that would look exactly like a real model-behavior difference.

    A context manager: `with LlmServerBackend(...) as backend:` calls start() on
    __enter__ and close() on __exit__. Callers that need to control the lifecycle
    explicitly (e.g. a Pulsar Function's lazy one-time setup) can call start()/
    close() directly instead. generate() raises LlmInferenceError if called before
    start() — unlike SubprocessLlmBackend, this backend has state, and there is no
    implicit auto-start.

    `LlmGenerationConfig.threads` is ignored here (same as HttpLlmBackend) — thread
    count is a server-startup concept, passed once via this class's own `threads`
    constructor argument, not a per-request one.
    """

    def __init__(
        self,
        binary_path: str | Path | None = None,
        model_path: str | Path | None = None,
        *,
        threads: int = 4,
        host: str = "127.0.0.1",
        port: int | None = None,
        startup_timeout_seconds: float = 60.0,
        mock: bool | None = None,
        extra_args: tuple[str, ...] = (),
    ) -> None:
        self._binary_path = Path(binary_path).expanduser() if binary_path else None
        self._model_path = Path(model_path).expanduser() if model_path else None
        self._threads = threads
        self._host = host
        self._port = port
        self._startup_timeout_seconds = startup_timeout_seconds
        self._mock = mock if mock is not None else _mock_enabled_via_env()
        self._extra_args = extra_args
        self._process: subprocess.Popen | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def start(self) -> Self:
        """Idempotent — a second call is a cheap no-op once the server is up, so
        callers with a lazy-configure-then-call-many-times shape (LlmTriageFunction)
        can call this unconditionally on every generate() without extra guard logic."""
        if self._mock or self._process is not None:
            return self
        self._check_binary_and_model_exist()
        if self._port is None:
            self._port = _find_free_port()
        command = [
            str(self._binary_path),
            "-m",
            str(self._model_path),
            "--host",
            self._host,
            "--port",
            str(self._port),
            "-t",
            str(self._threads),
            *self._extra_args,
        ]
        self._process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + self._startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                code = self._process.returncode
                self._process = None
                raise LlmInferenceError(f"llama-server exited during startup (code {code})")
            try:
                with urllib.request.urlopen(f"{self.base_url}/health", timeout=1.0) as response:
                    if response.status == 200:
                        return self
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(0.2)
        self.close()
        raise LlmInferenceError(f"llama-server did not become healthy within {self._startup_timeout_seconds}s")

    def close(self) -> None:
        """Terminates the server process. Safe to call multiple times, or before
        start() was ever called."""
        if self._process is None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=5.0)
        self._process = None

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def generate(self, prompt: str, config: LlmGenerationConfig | None = None) -> str:
        config = config or LlmGenerationConfig()
        if self._mock:
            return _mock_complete(prompt)
        if self._process is None:
            raise LlmInferenceError("LlmServerBackend.generate() called before start() — server is not running")

        payload: dict = {
            "prompt": prompt,
            "n_predict": config.max_tokens,
            "temperature": config.temperature,
        }
        if config.grammar:
            payload["grammar"] = config.grammar
        if config.stop:
            payload["stop"] = list(config.stop)

        request = urllib.request.Request(
            f"{self.base_url}/completion",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LlmInferenceError(f"llama-server returned HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LlmInferenceError(f"could not reach llama-server at {self.base_url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LlmInferenceError(f"llama-server did not respond within {config.timeout_seconds}s") from exc

        try:
            return body["content"].strip()
        except KeyError as exc:
            raise LlmInferenceError(f"unexpected response shape from llama-server: {body!r}") from exc

    def _check_binary_and_model_exist(self) -> None:
        if self._binary_path is None or not self._binary_path.exists():
            raise LlmInferenceError(
                f"llama-server binary not found at {self._binary_path!r}. Build it with "
                "`cmake -S . -B build -DLLAMA_BUILD_SERVER=ON && cmake --build build "
                "--target llama-server`, or construct with mock=True / set LLM_MOCK=1 "
                "to develop without it."
            )
        if self._model_path is None or not self._model_path.exists():
            raise LlmInferenceError(
                f"Model not found at {self._model_path!r}. Point model_path at a GGUF "
                "weights file, or construct with mock=True / set LLM_MOCK=1 to develop "
                "without it."
            )


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


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
