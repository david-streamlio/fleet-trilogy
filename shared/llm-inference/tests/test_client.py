import pytest
from llm_inference import LlmInferenceError, SubprocessLlmBackend


def test_mock_mode_returns_canned_completion_without_a_binary():
    backend = SubprocessLlmBackend(mock=True)
    completion = backend.generate("Write a short warning about traffic.")
    assert completion


def test_mock_mode_returns_json_for_structured_prompts():
    backend = SubprocessLlmBackend(mock=True)
    completion = backend.generate('Respond with ONLY a single JSON object with "event".')
    assert completion.strip().startswith("{")


def test_missing_binary_raises_a_clear_error(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_text("not a real model")
    backend = SubprocessLlmBackend(
        binary_path=tmp_path / "does-not-exist", model_path=model_path, mock=False
    )
    with pytest.raises(LlmInferenceError, match="LLM runtime binary not found"):
        backend.generate("hello")


def test_missing_model_raises_a_clear_error(tmp_path):
    binary_path = tmp_path / "main"
    binary_path.write_text("#!/bin/sh\n")
    binary_path.chmod(0o755)
    backend = SubprocessLlmBackend(
        binary_path=binary_path, model_path=tmp_path / "missing.gguf", mock=False
    )
    with pytest.raises(LlmInferenceError, match="Model not found"):
        backend.generate("hello")


def test_env_var_enables_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "1")
    backend = SubprocessLlmBackend()
    assert backend.generate("hello")
