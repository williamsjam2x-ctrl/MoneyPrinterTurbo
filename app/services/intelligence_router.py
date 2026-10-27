"""Optional, cost-bounded text-model router for the MoneyPrinterTurbo intelligence layer.

This module is deliberately separate from the existing video-generation path.
It uses OpenAI-compatible chat-completions endpoints and does not start jobs,
publish videos, or change the configured MoneyPrinterTurbo LLM provider.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from openai import OpenAI


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    provider_id: str
    base_url: str
    api_key_env: str
    model_env: str


@dataclass(frozen=True, slots=True)
class TextResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


PROVIDERS: dict[str, ProviderConfig] = {
    "codecraft": ProviderConfig(
        provider_id="codecraft",
        base_url="https://codecraftapi.com/v1",
        api_key_env="CODECRAFT_API_KEY",
        model_env="CODECRAFT_MODEL",
    ),
    "apinex": ProviderConfig(
        provider_id="apinex",
        base_url="https://api.apinex.bond/v1",
        api_key_env="APINEX_API_KEY",
        model_env="APINEX_MODEL",
    ),
    "openai": ProviderConfig(
        provider_id="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        model_env="OPENAI_MODEL",
    ),
}

ALLOWED_TASKS = frozenset(
    {"research_plan", "topic_score", "script_draft", "script_review", "quality_check"}
)
DEFAULT_PROVIDER_ORDER = ("codecraft", "apinex", "openai")
MAX_PROMPT_CHARS = 30_000
DEFAULT_MAX_OUTPUT_TOKENS = 1_200
MAX_OUTPUT_TOKENS = 2_000
REQUEST_TIMEOUT_SECONDS = 45.0


class IntelligenceRouterError(RuntimeError):
    """Raised when no configured provider can complete an intelligence request."""


def _provider_order(provider_order: Iterable[str] | None) -> tuple[str, ...]:
    if provider_order is not None:
        requested = tuple(provider_order)
    else:
        raw = os.getenv("MPT_INTELLIGENCE_PROVIDER_ORDER", "")
        requested = tuple(part.strip().lower() for part in raw.split(",") if part.strip())
        if not requested:
            requested = DEFAULT_PROVIDER_ORDER

    unknown = [name for name in requested if name not in PROVIDERS]
    if unknown:
        raise ValueError(f"Unknown intelligence provider(s): {', '.join(unknown)}")
    # Preserve order but avoid duplicate calls to the same provider.
    return tuple(dict.fromkeys(requested))


def _configured_provider(provider_id: str) -> tuple[ProviderConfig, str, str] | None:
    config = PROVIDERS[provider_id]
    api_key = os.getenv(config.api_key_env, "").strip()
    model = os.getenv(config.model_env, "").strip()
    if not api_key or not model:
        return None
    return config, api_key, model


def generate_text(
    *,
    task: str,
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    provider_order: Iterable[str] | None = None,
) -> TextResult:
    """Generate text using the first configured provider that succeeds.

    Provider model IDs are intentionally supplied through environment variables:
    they must match the user's current provider dashboard. Keys are never logged.
    Fallback happens only after an actual request failure; unconfigured providers
    are skipped without making a network request.
    """
    if task not in ALLOWED_TASKS:
        raise ValueError(f"Unsupported intelligence task: {task}")
    if not system_prompt.strip() or not user_prompt.strip():
        raise ValueError("Both system_prompt and user_prompt must be non-empty.")
    if len(system_prompt) + len(user_prompt) > MAX_PROMPT_CHARS:
        raise ValueError(f"Combined prompt exceeds {MAX_PROMPT_CHARS} characters.")
    if not 1 <= max_output_tokens <= MAX_OUTPUT_TOKENS:
        raise ValueError(f"max_output_tokens must be between 1 and {MAX_OUTPUT_TOKENS}.")

    failures: list[str] = []
    for provider_id in _provider_order(provider_order):
        configured = _configured_provider(provider_id)
        if configured is None:
            continue
        config, api_key, model = configured
        try:
            client = OpenAI(
                api_key=api_key,
                base_url=config.base_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                max_retries=0,
            )
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"Task: {task}.\n{system_prompt}"},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_output_tokens,
                temperature=0.2,
            )
            content = response.choices[0].message.content if response.choices else None
            if not isinstance(content, str) or not content.strip():
                failures.append(f"{provider_id}: empty response")
                continue
            usage = getattr(response, "usage", None)
            return TextResult(
                content=content.strip(),
                provider=provider_id,
                model=model,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
            )
        except Exception as exc:  # noqa: BLE001 - fallback must cover provider SDK errors.
            # Keep diagnostics useful without logging request content or credentials.
            failures.append(f"{provider_id}: {type(exc).__name__}")

    if not failures:
        raise IntelligenceRouterError(
            "No intelligence provider is configured. Set a provider API key and model ID."
        )
    raise IntelligenceRouterError(
        "All configured intelligence providers failed (" + "; ".join(failures) + ")."
    )
