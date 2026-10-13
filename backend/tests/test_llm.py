"""The Ollama client, against a mocked HTTP transport: request shape, errors, and the offline
guarantee that it never asks Ollama to download anything."""

import httpx
import pytest

from app.core.errors import LLMTimeoutError, LLMUnavailableError, ModelNotInstalledError
from app.llm.ollama import OllamaClient

CHAT_REPLY = {
    "model": "qwen3:0.6b",
    "message": {"role": "assistant", "content": "  Rack four. [#1]  "},
    "total_duration": 1_250_000_000,
    "load_duration": 50_000_000,
    "prompt_eval_count": 90,
    "eval_count": 12,
}


def client_for(handler, **kwargs) -> tuple[OllamaClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    llm = OllamaClient(
        "http://ollama:11434", "qwen3:0.6b", transport=httpx.MockTransport(record), **kwargs
    )
    return llm, seen


def test_chat_returns_trimmed_text_and_timings_in_milliseconds():
    llm, _ = client_for(lambda r: httpx.Response(200, json=CHAT_REPLY))

    result = llm.chat([{"role": "user", "content": "Where?"}])

    assert (result.text, result.total_ms, result.load_ms, result.output_tokens) == (
        "Rack four. [#1]",
        1250,
        50,
        12,
    )


def test_chat_sends_a_non_streaming_request_with_thinking_disabled():
    llm, seen = client_for(lambda r: httpx.Response(200, json=CHAT_REPLY))

    llm.chat([{"role": "user", "content": "Where?"}])

    payload = httpx.Response(200, content=seen[0].content).json()
    assert (payload["stream"], payload["think"], payload["model"]) == (False, False, "qwen3:0.6b")


def test_chat_omits_the_think_flag_when_unset():
    llm, seen = client_for(lambda r: httpx.Response(200, json=CHAT_REPLY), think=None)

    llm.chat([{"role": "user", "content": "Where?"}])

    assert "think" not in httpx.Response(200, content=seen[0].content).json()


def test_chat_raises_model_not_installed_with_a_hint_on_404():
    llm, _ = client_for(lambda r: httpx.Response(404, json={"error": "model not found"}))

    with pytest.raises(ModelNotInstalledError) as error:
        llm.chat([{"role": "user", "content": "Where?"}])

    assert "offline-install.sh" in error.value.hint


def test_chat_raises_llm_unavailable_when_ollama_refuses_connections():
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    llm, _ = client_for(refuse)

    with pytest.raises(LLMUnavailableError):
        llm.chat([{"role": "user", "content": "Where?"}])


def test_chat_raises_llm_timeout_when_inference_takes_too_long():
    def slow(request):
        raise httpx.ReadTimeout("timed out", request=request)

    llm, _ = client_for(slow)

    with pytest.raises(LLMTimeoutError):
        llm.chat([{"role": "user", "content": "Where?"}])


def test_info_reports_a_missing_model_without_trying_to_download_it():
    routes = {
        "/api/version": {"version": "0.40.3"},
        "/api/tags": {"models": [{"name": "other:1b"}]},
    }
    llm, seen = client_for(lambda r: httpx.Response(200, json=routes[r.url.path]))

    info = llm.info()

    assert info.installed is False
    assert [r.url.path for r in seen] == ["/api/version", "/api/tags"]


def test_client_has_no_way_to_pull_a_model():
    # The offline guarantee is structural: there is no code path that downloads a model.
    assert not any("pull" in name for name in dir(OllamaClient))
