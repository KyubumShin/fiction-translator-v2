"""Tests for LLM provider logic."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fiction_translator.llm.providers import (
    ClaudeProvider,
    GeminiProvider,
    LLMResponse,
    OpenAIProvider,
    get_available_providers,
    get_llm_provider,
)


class TestGetLLMProvider:
    """Tests for get_llm_provider factory function."""

    def test_returns_gemini_provider(self):
        provider = get_llm_provider("gemini", api_keys={"gemini": "test-key"})
        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == "test-key"

    def test_returns_claude_provider(self):
        provider = get_llm_provider("claude", api_keys={"claude": "test-key"})
        assert isinstance(provider, ClaudeProvider)
        assert provider.api_key == "test-key"

    def test_returns_openai_provider(self):
        provider = get_llm_provider("openai", api_keys={"openai": "test-key"})
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test-key"

    def test_accepts_google_key_for_gemini(self):
        """Test that 'google' key alias works for Gemini."""
        provider = get_llm_provider("gemini", api_keys={"google": "test-key"})
        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == "test-key"

    def test_accepts_anthropic_key_for_claude(self):
        """Test that 'anthropic' key alias works for Claude."""
        provider = get_llm_provider("claude", api_keys={"anthropic": "test-key"})
        assert isinstance(provider, ClaudeProvider)
        assert provider.api_key == "test-key"

    def test_prefers_primary_key_over_alias(self):
        """Test that primary key name takes precedence over alias."""
        provider = get_llm_provider(
            "gemini", api_keys={"gemini": "primary-key", "google": "alias-key"}
        )
        assert provider.api_key == "primary-key"

    def test_raises_for_unknown_provider(self):
        """Test that unknown provider name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            get_llm_provider("unknown", api_keys={"unknown": "test-key"})

    def test_raises_when_api_key_missing(self):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError, match="No API key provided for gemini"):
            get_llm_provider("gemini", api_keys={})

    def test_accepts_custom_model(self):
        """Test that custom model parameter is passed to provider."""
        provider = get_llm_provider(
            "gemini", api_keys={"gemini": "test-key"}, model="gemini-pro"
        )
        assert provider.model == "gemini-pro"

    def test_default_model_used_when_not_specified(self):
        """Test that default model is used when not specified."""
        provider = get_llm_provider("gemini", api_keys={"gemini": "test-key"})
        assert provider.model == "gemini-2.0-flash"


class TestGetAvailableProviders:
    """Tests for get_available_providers function."""

    def test_returns_all_providers_when_all_keys_present(self):
        api_keys = {"gemini": "key1", "claude": "key2", "openai": "key3"}
        available = get_available_providers(api_keys)
        assert set(available) == {"gemini", "claude", "openai"}

    def test_returns_gemini_only(self):
        api_keys = {"gemini": "key1"}
        available = get_available_providers(api_keys)
        assert available == ["gemini"]

    def test_returns_empty_when_no_keys(self):
        api_keys = {}
        available = get_available_providers(api_keys)
        assert available == []

    def test_accepts_google_alias_for_gemini(self):
        api_keys = {"google": "key1"}
        available = get_available_providers(api_keys)
        assert "gemini" in available

    def test_accepts_anthropic_alias_for_claude(self):
        api_keys = {"anthropic": "key1"}
        available = get_available_providers(api_keys)
        assert "claude" in available


class TestProviderIsAvailable:
    """Tests for provider is_available method."""

    def test_gemini_available_with_key(self):
        provider = GeminiProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_gemini_not_available_without_key(self):
        provider = GeminiProvider(api_key="")
        assert provider.is_available() is False

    def test_claude_available_with_key(self):
        provider = ClaudeProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_claude_not_available_without_key(self):
        provider = ClaudeProvider(api_key="")
        assert provider.is_available() is False

    def test_openai_available_with_key(self):
        provider = OpenAIProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_openai_not_available_without_key(self):
        provider = OpenAIProvider(api_key="")
        assert provider.is_available() is False


@pytest.mark.asyncio
class TestGenerateJSON:
    """Tests for LLMProvider.generate_json method."""

    async def test_parses_valid_json(self):
        """Test that valid JSON is parsed correctly."""
        provider = GeminiProvider(api_key="test-key")

        # Mock the generate method
        provider.generate = AsyncMock(
            return_value=LLMResponse(
                text='{"key": "value"}', model="test", usage={}
            )
        )

        result = await provider.generate_json("test prompt")
        assert result == {"key": "value"}

    async def test_extracts_json_from_markdown_code_block(self):
        """Test that JSON in markdown code blocks is extracted."""
        provider = GeminiProvider(api_key="test-key")

        # Mock the generate method with markdown-wrapped JSON
        provider.generate = AsyncMock(
            return_value=LLMResponse(
                text='```json\n{"key": "value"}\n```', model="test", usage={}
            )
        )

        result = await provider.generate_json("test prompt")
        assert result == {"key": "value"}

    async def test_extracts_json_from_code_block_without_language(self):
        """Test that JSON in code blocks without 'json' label is extracted."""
        provider = GeminiProvider(api_key="test-key")

        provider.generate = AsyncMock(
            return_value=LLMResponse(
                text='```\n{"key": "value"}\n```', model="test", usage={}
            )
        )

        result = await provider.generate_json("test prompt")
        assert result == {"key": "value"}

    async def test_raises_value_error_for_invalid_json(self):
        """Test that invalid JSON raises ValueError."""
        provider = GeminiProvider(api_key="test-key")

        provider.generate = AsyncMock(
            return_value=LLMResponse(
                text='not valid json', model="test", usage={}
            )
        )

        with pytest.raises(ValueError, match="LLM did not return valid JSON"):
            await provider.generate_json("test prompt")

    async def test_appends_json_instruction_to_system_prompt(self):
        """Test that generate_json adds JSON instruction to system prompt."""
        provider = GeminiProvider(api_key="test-key")

        provider.generate = AsyncMock(
            return_value=LLMResponse(
                text='{"key": "value"}', model="test", usage={}
            )
        )

        await provider.generate_json(
            "test prompt", system_prompt="Original prompt"
        )

        # Check that generate was called with the modified system prompt
        call_args = provider.generate.call_args
        assert "Original prompt" in call_args.kwargs["system_prompt"]
        assert "Respond with valid JSON only" in call_args.kwargs["system_prompt"]


@pytest.mark.asyncio
class TestRetryLogic:
    """Tests for LLM provider retry logic."""

    async def test_retries_on_429_rate_limit(self):
        """Test that 429 status triggers retry."""
        provider = GeminiProvider(api_key="test-key", model="test-model")

        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limit", request=MagicMock(), response=mock_response_429
        )

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "success"}]}}],
            "usageMetadata": {},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(
                side_effect=[mock_response_429, mock_response_success]
            )
            mock_client.return_value = mock_context

            # Should succeed after retry
            result = await provider.generate("test prompt")
            assert result.text == "success"

    async def test_does_not_retry_on_400_client_error(self):
        """Test that 400 status does not trigger retry."""
        provider = GeminiProvider(api_key="test-key", model="test-model")

        mock_response = MagicMock()
        mock_response.status_code = 400
        error = httpx.HTTPStatusError(
            "Bad request", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(side_effect=error)
            mock_client.return_value = mock_context

            # Should raise immediately without retry
            with pytest.raises(httpx.HTTPStatusError):
                await provider.generate("test prompt")

            # Should only be called once (no retries)
            assert mock_context.__aenter__.return_value.post.call_count == 1

    async def test_does_not_retry_on_404_not_found(self):
        """Test that 404 status does not trigger retry."""
        provider = GeminiProvider(api_key="test-key", model="test-model")

        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(side_effect=error)
            mock_client.return_value = mock_context

            with pytest.raises(httpx.HTTPStatusError):
                await provider.generate("test prompt")

            # Should only be called once (no retries)
            assert mock_context.__aenter__.return_value.post.call_count == 1

    async def test_retries_on_500_server_error(self):
        """Test that 500 status triggers retry."""
        provider = GeminiProvider(api_key="test-key", model="test-model")

        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        error = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response_500
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(side_effect=error)
            mock_client.return_value = mock_context

            with pytest.raises(httpx.HTTPStatusError):
                await provider.generate("test prompt")

            # Should retry (3 attempts total)
            assert mock_context.__aenter__.return_value.post.call_count == 3

    async def test_retries_on_connection_error(self):
        """Test that connection errors trigger retry."""
        provider = GeminiProvider(api_key="test-key", model="test-model")

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )
            mock_client.return_value = mock_context

            with pytest.raises(httpx.ConnectError):
                await provider.generate("test prompt")

            # Should retry (3 attempts total)
            assert mock_context.__aenter__.return_value.post.call_count == 3

    async def test_retries_on_timeout(self):
        """Test that timeout errors trigger retry."""
        provider = GeminiProvider(api_key="test-key", model="test-model")

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ReadTimeout("Timeout")
            )
            mock_client.return_value = mock_context

            with pytest.raises(httpx.ReadTimeout):
                await provider.generate("test prompt")

            # Should retry (3 attempts total)
            assert mock_context.__aenter__.return_value.post.call_count == 3
