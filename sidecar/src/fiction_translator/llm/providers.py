"""
LLM Provider Abstraction Layer - Ported from v1 with enhancements.

Provides unified interface for multiple LLM APIs:
- Google Gemini (default)
- Anthropic Claude
- OpenAI GPT
"""
from __future__ import annotations

import asyncio as _asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAX_LLM_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds


async def _retry_generate(coro_factory, max_retries=MAX_LLM_RETRIES):
    """Retry an async LLM call with exponential backoff.

    Parameters
    ----------
    coro_factory : callable
        A zero-argument callable that returns a new coroutine each time.
    max_retries : int
        Maximum number of attempts.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code
            # Don't retry client errors (except 429 rate limit)
            if 400 <= status < 500 and status != 429:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "LLM API error (attempt %d/%d, status %d): %s. Retrying in %.1fs...",
                attempt + 1, max_retries, status, e, delay,
            )
            await _asyncio.sleep(delay)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
            last_error = e
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "LLM connection error (attempt %d/%d): %s. Retrying in %.1fs...",
                attempt + 1, max_retries, e, delay,
            )
            await _asyncio.sleep(delay)
    raise last_error


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    text: str
    model: str
    usage: dict
    raw_response: Any | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate text completion."""
        pass

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict:
        """Generate and parse JSON response."""
        response = await self.generate(
            prompt=prompt,
            system_prompt=(system_prompt or "") + "\n\nRespond with valid JSON only.",
            temperature=temperature,
            max_tokens=max_tokens,
        )

        text = response.text.strip()

        # Handle markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Raw response: {response.text}")
            raise ValueError(f"LLM did not return valid JSON: {e}") from e

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Gemini API key not configured")

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "topP": 0.9,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        async def _call():
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()

        data = await _retry_generate(_call)

        # Extract text from response
        text = data["candidates"][0]["content"]["parts"][0]["text"]

        # Extract usage if available
        usage = {}
        if "usageMetadata" in data:
            usage = {
                "prompt_tokens": data["usageMetadata"].get("promptTokenCount", 0),
                "completion_tokens": data["usageMetadata"].get("candidatesTokenCount", 0),
            }

        return LLMResponse(
            text=text,
            model=self.model,
            usage=usage,
            raw_response=data,
        )


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("Anthropic API key not configured")

        url = f"{self.base_url}/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }

        if system_prompt:
            payload["system"] = system_prompt

        async def _call():
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()

        data = await _retry_generate(_call)

        # Extract text from response
        text = data["content"][0]["text"]

        usage = {
            "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
            "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
        }

        return LLMResponse(
            text=text,
            model=self.model,
            usage=usage,
            raw_response=data,
        )


class OpenAIProvider(LLMProvider):
    """OpenAI GPT API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("OpenAI API key not configured")

        url = f"{self.base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async def _call():
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()

        data = await _retry_generate(_call)

        # Extract text from response
        text = data["choices"][0]["message"]["content"]

        usage = {
            "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
            "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
        }

        return LLMResponse(
            text=text,
            model=self.model,
            usage=usage,
            raw_response=data,
        )


# Provider registry
PROVIDERS = {
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
}


def get_llm_provider(
    provider_name: str = "gemini",
    api_keys: dict[str, str] | None = None,
    model: str | None = None,
) -> LLMProvider:
    """
    Factory function to get an LLM provider.

    Args:
        provider_name: One of 'gemini', 'claude', 'openai'. Defaults to 'gemini'
        api_keys: Dict mapping provider names to API keys.
                 Keys: 'gemini'/'google', 'claude'/'anthropic', 'openai'
        model: Optional model override

    Returns:
        Configured LLMProvider instance

    Raises:
        ValueError: If provider name is unknown or API key is missing
    """
    keys = api_keys or {}

    if provider_name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(PROVIDERS.keys())}")

    provider_class = PROVIDERS[provider_name]

    # Map provider name to API key
    if provider_name == "gemini":
        api_key = keys.get("gemini") or keys.get("google")
    elif provider_name == "claude":
        api_key = keys.get("claude") or keys.get("anthropic")
    elif provider_name == "openai":
        api_key = keys.get("openai")
    else:
        api_key = None

    if not api_key:
        raise ValueError(f"No API key provided for {provider_name}")

    kwargs = {"api_key": api_key}
    if model:
        kwargs["model"] = model

    return provider_class(**kwargs)


def get_available_providers(api_keys: dict[str, str]) -> list[str]:
    """
    Return list of providers that have API keys configured.

    Args:
        api_keys: Dict mapping provider names to API keys

    Returns:
        List of available provider names
    """
    available = []

    # Check each provider
    if api_keys.get("gemini") or api_keys.get("google"):
        available.append("gemini")
    if api_keys.get("claude") or api_keys.get("anthropic"):
        available.append("claude")
    if api_keys.get("openai"):
        available.append("openai")

    return available
