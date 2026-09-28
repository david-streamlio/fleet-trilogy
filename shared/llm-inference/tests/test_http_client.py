import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from llm_inference import HttpLlmBackend, LlmGenerationConfig, LlmInferenceError


class _FakeOpenAiServer:
    """A minimal local OpenAI-chat-completions-shaped server for testing the
    HTTP request/response plumbing without any real model or network call."""

    def __init__(self, *, status: int = 200, reply_text: str = "ok", body: dict | None = None) -> None:
        self.status = status
        self.reply_text = reply_text
        self.body = body
        self.last_request_json: dict | None = None
        self.last_auth_header: str | None = None

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - http.server naming convention
                length = int(self.headers.get("Content-Length", 0))
                outer.last_request_json = json.loads(self.rfile.read(length))
                outer.last_auth_header = self.headers.get("Authorization")
                self.send_response(outer.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response_body = outer.body
                if response_body is None:
                    response_body = {"choices": [{"message": {"content": outer.reply_text}}]}
                self.wfile.write(json.dumps(response_body).encode("utf-8"))

            def log_message(self, *args) -> None:  # silence test output
                pass

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}/v1"

    def __enter__(self) -> "_FakeOpenAiServer":
        self._thread.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self._server.shutdown()
        self._server.server_close()


def test_mock_mode_returns_canned_completion_without_a_server():
    backend = HttpLlmBackend(base_url="http://unused", model="tiny", mock=True)
    completion = backend.generate("Write a short warning about traffic.")
    assert completion


def test_generate_sends_openai_shaped_request_and_parses_reply():
    with _FakeOpenAiServer(reply_text="hello from the engine") as server:
        backend = HttpLlmBackend(base_url=server.base_url, model="tiny", api_key="secret-key")
        result = backend.generate("hi", LlmGenerationConfig(max_tokens=32, temperature=0.1))

    assert result == "hello from the engine"
    assert server.last_request_json == {
        "model": "tiny",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 32,
        "temperature": 0.1,
    }
    assert server.last_auth_header == "Bearer secret-key"


def test_generate_without_api_key_sends_no_auth_header():
    with _FakeOpenAiServer() as server:
        backend = HttpLlmBackend(base_url=server.base_url, model="tiny")
        backend.generate("hi")

    assert server.last_auth_header is None


def test_http_error_status_raises_llm_inference_error():
    with _FakeOpenAiServer(status=500, body={"error": "engine overloaded"}) as server:
        backend = HttpLlmBackend(base_url=server.base_url, model="tiny")
        with pytest.raises(LlmInferenceError, match="HTTP 500"):
            backend.generate("hi")


def test_unexpected_response_shape_raises_llm_inference_error():
    with _FakeOpenAiServer(body={"unexpected": "shape"}) as server:
        backend = HttpLlmBackend(base_url=server.base_url, model="tiny")
        with pytest.raises(LlmInferenceError, match="unexpected response shape"):
            backend.generate("hi")


def test_unreachable_server_raises_a_clear_error():
    backend = HttpLlmBackend(base_url="http://127.0.0.1:1", model="tiny")
    with pytest.raises(LlmInferenceError, match="could not reach"):
        backend.generate("hi", LlmGenerationConfig(timeout_seconds=2.0))
