"""Coverage for provider response parsing and client shutdown paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


@pytest.mark.asyncio
async def test_gemini_generate_and_vision_parse_text(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from backend.adapters.gemini_adapter import GeminiAdapter

    adapter = GeminiAdapter()
    response = _response({"candidates": [{"content": {"parts": [{"text": "answer"}]}}]})
    adapter._client = MagicMock()
    adapter._client.post = AsyncMock(return_value=response)

    assert await adapter.generate("prompt") == "answer"
    assert await adapter.vision("describe", image_b64="aW1hZ2U=") == "answer"
    await adapter.close()


@pytest.mark.asyncio
async def test_openrouter_generate_and_models_parse_response(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    from backend.adapters.openrouter_adapter import OpenRouterAdapter

    adapter = OpenRouterAdapter()
    adapter._client = MagicMock()
    adapter._client.post = AsyncMock(
        return_value=_response({"choices": [{"message": {"content": "answer"}}]})
    )
    adapter._client.get = AsyncMock(return_value=_response({"data": [{"id": "model-1"}]}))

    assert await adapter.generate("prompt") == "answer"
    assert await adapter.models() == [{"id": "model-1"}]
    await adapter.close()


@pytest.mark.asyncio
async def test_groq_generate_parses_response(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    from backend.adapters.groq_adapter import GroqAdapter

    adapter = GroqAdapter()
    adapter._client = MagicMock()
    adapter._client.post = AsyncMock(
        return_value=_response({"choices": [{"message": {"content": "answer"}}]})
    )

    assert await adapter.generate("prompt") == "answer"
    await adapter.close()


@pytest.mark.asyncio
async def test_ollama_response_parsers(monkeypatch) -> None:
    from backend.adapters.ollama_adapter import OllamaAdapter

    adapter = OllamaAdapter()
    adapter._client = MagicMock()
    adapter._client.post = AsyncMock(
        side_effect=[
            _response({"response": "generated"}),
            _response({"message": {"content": "chat"}}),
            _response({"response": "vision"}),
            _response({"embeddings": [[0.1, 0.2]]}),
        ]
    )

    assert await adapter.generate("prompt") == "generated"
    assert await adapter.chat([{"role": "user", "content": "hello"}]) == "chat"
    assert await adapter.vision("https://image.invalid/test.png") == "vision"
    assert await adapter.embed("text") == [0.1, 0.2]
    await adapter.close()


@pytest.mark.asyncio
async def test_dispatcher_closes_initialized_adapters_and_continues_after_error() -> None:
    from backend.dispatcher import RainGodDispatcher

    dispatcher = RainGodDispatcher()
    first = MagicMock()
    first.close = AsyncMock()
    broken = MagicMock()
    broken.close = AsyncMock(side_effect=RuntimeError("close failed"))
    last = MagicMock()
    last.close = AsyncMock()
    dispatcher._local = first
    dispatcher._groq = broken
    dispatcher._gemini = last

    await dispatcher.close()

    first.close.assert_awaited_once_with()
    broken.close.assert_awaited_once_with()
    last.close.assert_awaited_once_with()
