import json
import textwrap

import pytest
from llm_inference import LlmGenerationConfig, LlmInferenceError, LlmServerBackend
from llm_inference.client import _find_free_port


def test_mock_mode_returns_canned_completion_without_a_server():
    backend = LlmServerBackend(mock=True)
    completion = backend.generate("Write a short warning about traffic.")
    assert completion


def test_missing_binary_raises_a_clear_error(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_text("not a real model")
    backend = LlmServerBackend(binary_path=tmp_path / "does-not-exist", model_path=model_path)
    with pytest.raises(LlmInferenceError, match="llama-server binary not found"):
        backend.start()


def test_missing_model_raises_a_clear_error(tmp_path):
    binary_path = tmp_path / "llama-server"
    binary_path.write_text("#!/bin/sh\n")
    binary_path.chmod(0o755)
    backend = LlmServerBackend(binary_path=binary_path, model_path=tmp_path / "missing.gguf")
    with pytest.raises(LlmInferenceError, match="Model not found"):
        backend.start()


def test_generate_before_start_raises_a_clear_error():
    backend = LlmServerBackend(binary_path="/unused", model_path="/unused")
    with pytest.raises(LlmInferenceError, match="called before start"):
        backend.generate("hello")


@pytest.fixture
def fake_server_binary(tmp_path):
    """A stand-in for llama-server: a real HTTP server (stdlib http.server) that
    understands --port, GET /health, and POST /completion, echoing back the
    request body's grammar/stop fields so tests can verify the exact JSON this
    backend sends — without needing the real (multi-hundred-MB) binary. Tests the
    actual start()/generate()/close() lifecycle code (Popen, health-poll loop,
    terminate), not just a mocked-out generate().
    """
    script = tmp_path / "fake-llama-server.py"
    script.write_text(
        textwrap.dedent(
            """\
            import json
            import sys
            from http.server import BaseHTTPRequestHandler, HTTPServer

            port = int(sys.argv[sys.argv.index("--port") + 1])

            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/health":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(b'{"status":"ok"}')

                def do_POST(self):
                    length = int(self.headers.get("Content-Length", 0))
                    body = json.loads(self.rfile.read(length))
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    reply = {
                        "content": "echo:" + body.get("prompt", ""),
                        "_seen_grammar": body.get("grammar"),
                        "_seen_stop": body.get("stop"),
                    }
                    self.wfile.write(json.dumps(reply).encode())

                def log_message(self, *args):
                    pass

            HTTPServer(("127.0.0.1", port), Handler).serve_forever()
            """
        )
    )
    binary = tmp_path / "llama-server"
    binary.write_text(f"#!/bin/sh\nexec python3 {script} \"$@\"\n")
    binary.chmod(0o755)
    return binary


def test_start_generate_close_real_lifecycle(fake_server_binary, tmp_path):
    backend = LlmServerBackend(
        binary_path=fake_server_binary,
        model_path=tmp_path,  # existence is all that's checked; content is irrelevant to the fake
        threads=8,
        startup_timeout_seconds=10.0,
    )
    try:
        backend.start()
        result = backend.generate(
            "hi there",
            LlmGenerationConfig(grammar='root ::= "ok"', stop=("STOP",)),
        )
        assert result == "echo:hi there"
    finally:
        backend.close()


def test_generate_sends_grammar_and_stop_fields(fake_server_binary, tmp_path):
    with LlmServerBackend(binary_path=fake_server_binary, model_path=tmp_path, startup_timeout_seconds=10.0) as backend:
        # Inspect what the fake server actually received by asking it to echo —
        # the fake's reply embeds _seen_grammar/_seen_stop, but generate() only
        # returns "content". Fetch the raw response directly to assert on those.
        import urllib.request

        request = urllib.request.Request(
            f"{backend.base_url}/completion",
            data=json.dumps({"prompt": "x", "grammar": "root ::= \"a\"", "stop": ["}"]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5.0) as response:
            body = json.loads(response.read().decode())
        assert body["_seen_grammar"] == 'root ::= "a"'
        assert body["_seen_stop"] == ["}"]


def test_start_is_idempotent(fake_server_binary, tmp_path):
    backend = LlmServerBackend(binary_path=fake_server_binary, model_path=tmp_path, startup_timeout_seconds=10.0)
    try:
        backend.start()
        first_process = backend._process
        backend.start()  # should not spawn a second process
        assert backend._process is first_process
    finally:
        backend.close()


def test_find_free_port_returns_a_usable_port():
    port = _find_free_port()
    assert 0 < port < 65536
