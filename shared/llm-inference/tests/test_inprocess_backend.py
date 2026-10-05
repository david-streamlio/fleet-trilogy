import sys
import types
from typing import ClassVar

import pytest
from llm_inference import InProcessLlmBackend, LlmGenerationConfig, LlmInferenceError


class _FakeLlama:
    instances: ClassVar[list["_FakeLlama"]] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.calls: list[tuple[str, dict]] = []
        _FakeLlama.instances.append(self)

    def create_completion(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return {"choices": [{"text": '  {"spoken_warning": "On I-95N, slow down."}\n'}]}


class _StoppingCriteriaList(list):
    def __call__(self, input_ids, logits) -> bool:
        return any(criterion(input_ids, logits) for criterion in self)


@pytest.fixture
def fake_llama_cpp(monkeypatch):
    _FakeLlama.instances = []
    module = types.ModuleType("llama_cpp")
    module.Llama = _FakeLlama
    module.StoppingCriteriaList = _StoppingCriteriaList
    monkeypatch.setitem(sys.modules, "llama_cpp", module)
    return module


@pytest.fixture
def model_path(tmp_path):
    path = tmp_path / "model.gguf"
    path.write_text("not a real model")
    return path


def test_mock_mode_returns_canned_completion_without_llama_cpp():
    backend = InProcessLlmBackend(mock=True)
    assert backend.generate("Write a short warning about traffic.")


def test_missing_model_raises_a_clear_error(tmp_path, fake_llama_cpp):
    backend = InProcessLlmBackend(tmp_path / "missing.gguf", mock=False)
    with pytest.raises(LlmInferenceError, match="Model not found"):
        backend.generate("hello")


def test_missing_llama_cpp_raises_a_clear_error(monkeypatch, model_path):
    monkeypatch.setitem(sys.modules, "llama_cpp", None)  # makes the import fail
    backend = InProcessLlmBackend(model_path, mock=False)
    with pytest.raises(LlmInferenceError, match="llama-cpp-python is not installed"):
        backend.generate("hello")


def test_model_loads_once_and_is_reused(fake_llama_cpp, model_path):
    backend = InProcessLlmBackend(model_path, threads=1, mock=False)
    assert backend.generate("first") == '{"spoken_warning": "On I-95N, slow down."}'
    backend.generate("second")
    assert len(_FakeLlama.instances) == 1
    assert [prompt for prompt, _ in _FakeLlama.instances[0].calls] == ["first", "second"]


def test_cpu_only_by_default_including_llama_cpps_automatic_offloads(
    fake_llama_cpp, model_path
):
    InProcessLlmBackend(model_path, threads=1, mock=False).load()
    kwargs = _FakeLlama.instances[0].kwargs
    assert kwargs["n_threads"] == kwargs["n_threads_batch"] == 1
    assert kwargs["n_gpu_layers"] == 0
    assert kwargs["op_offload"] is False
    assert kwargs["offload_kqv"] is False


def test_gpu_layers_turn_the_offloads_back_on(fake_llama_cpp, model_path):
    InProcessLlmBackend(model_path, gpu_layers=-1, mock=False).load()
    kwargs = _FakeLlama.instances[0].kwargs
    assert kwargs["op_offload"] is True
    assert kwargs["offload_kqv"] is True


def test_generation_settings_are_passed_through(fake_llama_cpp, model_path):
    backend = InProcessLlmBackend(model_path, mock=False)
    backend.generate(
        "hello", LlmGenerationConfig(max_tokens=64, temperature=0.2, stop=("\n\n",))
    )
    _, kwargs = _FakeLlama.instances[0].calls[0]
    assert kwargs["max_tokens"] == 64
    assert kwargs["temperature"] == 0.2
    assert kwargs["stop"] == ["\n\n"]


def test_timeout_stops_generation_and_raises(fake_llama_cpp, model_path, monkeypatch):
    def slow_completion(self, prompt, **kwargs):
        # The stopping criterion is what llama-cpp-python checks between tokens.
        assert kwargs["stopping_criteria"](None, None)
        return {"choices": [{"text": "partial"}]}

    monkeypatch.setattr(_FakeLlama, "create_completion", slow_completion)
    backend = InProcessLlmBackend(model_path, mock=False)
    with pytest.raises(LlmInferenceError, match="did not finish within"):
        backend.generate("hello", LlmGenerationConfig(timeout_seconds=-1))


def test_seed_is_random_unless_pinned(fake_llama_cpp, model_path):
    InProcessLlmBackend(model_path, mock=False).load()
    InProcessLlmBackend(model_path, mock=False).load()
    InProcessLlmBackend(model_path, seed=7, mock=False).load()
    seeds = [llama.kwargs["seed"] for llama in _FakeLlama.instances]
    assert seeds[0] != seeds[1]
    assert seeds[2] == 7
