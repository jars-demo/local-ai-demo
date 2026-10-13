"""The only path to a language model: Ollama's HTTP API on the private Docker network.

Deliberately small. It can chat with an installed model and describe it. It has no method to pull
or download a model and no fallback provider, so a missing model is an error the operator fixes
(by restoring the offline bundle), never a silent download or a call to an external API.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.errors import LLMError, LLMTimeoutError, LLMUnavailableError, ModelNotInstalledError

log = logging.getLogger("app.llm")

INSTALL_HINT = (
    "Connected machine: ./scripts/pull-model.sh. "
    "Offline server: restore the model from the bundle with ./scripts/offline-install.sh."
)


@dataclass
class ChatResult:
    text: str
    model: str
    total_ms: int
    load_ms: int
    prompt_tokens: int
    output_tokens: int


@dataclass
class ModelInfo:
    name: str
    installed: bool
    ollama_version: str | None = None
    size_bytes: int | None = None
    digest: str | None = None
    family: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    context_length: int | None = None


class LLM(Protocol):
    model: str

    def chat(self, messages: list[dict], *, max_tokens: int | None = None) -> ChatResult: ...
    def info(self) -> ModelInfo: ...


def _ms(nanoseconds: int | None) -> int:
    return round((nanoseconds or 0) / 1_000_000)


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        think: bool | None = False,
        timeout_seconds: float = 180.0,
        max_tokens: int = 384,
        context_tokens: int = 4096,
        transport: httpx.BaseTransport | None = None,
    ):
        self.model = model
        self.think = think
        self.max_tokens = max_tokens
        self.context_tokens = context_tokens
        self.http = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_seconds, connect=5.0),
            transport=transport,
        )

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            return self.http.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                "The local model did not answer in time.",
                hint="CPU inference is slow on small machines. Raise LLM_TIMEOUT_SECONDS or ask a "
                "shorter question.",
            ) from exc
        except httpx.TransportError as exc:
            raise LLMUnavailableError(
                f"Ollama is not reachable at {self.http.base_url}.",
                hint="Check `docker compose ps ollama` and `docker compose logs ollama`.",
            ) from exc

    def chat(self, messages: list[dict], *, max_tokens: int | None = None) -> ChatResult:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": max_tokens or self.max_tokens,
                "num_ctx": self.context_tokens,
            },
        }
        if self.think is not None:
            payload["think"] = self.think
        response = self._request("POST", "/api/chat", json=payload)
        if response.status_code == 404:
            raise ModelNotInstalledError(
                f"The model {self.model} is not installed in Ollama.", hint=INSTALL_HINT
            )
        if response.status_code != 200:
            raise LLMError(f"Ollama returned HTTP {response.status_code}: {response.text[:200]}")
        data = response.json()
        text = (data.get("message") or {}).get("content", "").strip()
        if not text:
            raise LLMError("The model returned an empty answer.")
        result = ChatResult(
            text=text,
            model=data.get("model", self.model),
            total_ms=_ms(data.get("total_duration")),
            load_ms=_ms(data.get("load_duration")),
            prompt_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )
        log.info(
            "inference completed",
            extra={
                "model": result.model,
                "total_ms": result.total_ms,
                "load_ms": result.load_ms,
                "prompt_tokens": result.prompt_tokens,
                "output_tokens": result.output_tokens,
            },
        )
        return result

    def info(self) -> ModelInfo:
        version = self._request("GET", "/api/version").json().get("version")
        tags = self._request("GET", "/api/tags").json().get("models", [])
        match = next((m for m in tags if m.get("name") == self.model), None)
        if match is None:
            return ModelInfo(name=self.model, installed=False, ollama_version=version)
        details = match.get("details") or {}
        context_length = None
        show = self._request("POST", "/api/show", json={"model": self.model})
        if show.status_code == 200:
            model_info = show.json().get("model_info") or {}
            context_length = next(
                (v for k, v in model_info.items() if k.endswith(".context_length")), None
            )
        return ModelInfo(
            name=self.model,
            installed=True,
            ollama_version=version,
            size_bytes=match.get("size"),
            digest=match.get("digest"),
            family=details.get("family"),
            parameter_size=details.get("parameter_size"),
            quantization=details.get("quantization_level"),
            context_length=context_length,
        )
