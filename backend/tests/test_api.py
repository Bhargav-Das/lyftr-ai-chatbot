import pytest
import pytest_asyncio

from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app


# ============================================================
# TEST CLIENT FIXTURE
# ============================================================

@pytest_asyncio.fixture
async def client():
    """
    Creates an asynchronous HTTP client that communicates
    directly with the FastAPI application.

    No real HTTP server needs to be running for these tests.
    """

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client


# ============================================================
# 1. HEALTH CHECK
# ============================================================

@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["keys_configured"] >= 2
    assert data["cache_enabled"] is True


# ============================================================
# 2. EMPTY MESSAGE -> 422
# ============================================================

@pytest.mark.asyncio
async def test_empty_message_returns_422(client):
    response = await client.post(
        "/chat",
        json={
            "session_id": "validation-test",
            "message": "   ",
        },
    )

    assert response.status_code == 422


# ============================================================
# 3. EMPTY SESSION ID -> 422
# ============================================================

@pytest.mark.asyncio
async def test_empty_session_id_returns_422(client):
    response = await client.post(
        "/chat",
        json={
            "session_id": "   ",
            "message": "Hello",
        },
    )

    assert response.status_code == 422


# ============================================================
# 4. MESSAGE > 4000 CHARACTERS -> 422
# ============================================================

@pytest.mark.asyncio
async def test_message_too_long_returns_422(client):
    response = await client.post(
        "/chat",
        json={
            "session_id": "long-message-test",
            "message": "a" * 4001,
        },
    )

    assert response.status_code == 422


# ============================================================
# 5. UNKNOWN SESSION -> 404
# ============================================================

@pytest.mark.asyncio
async def test_unknown_session_returns_404(client):
    response = await client.get(
        "/sessions/"
        "definitely-not-a-real-session-xyz/"
        "messages"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "session not found"
    }


# ============================================================
# 6. ALL PROVIDERS FAIL -> 503
#    FAILED REQUEST MUST NOT BE STORED
# ============================================================

@pytest.mark.asyncio
async def test_all_provider_failure_returns_503(
    client,
):
    session_id = "pytest-all-provider-failure"

    response = await client.post(
        "/chat",
        headers={
            "X-Simulate-Failure": "*=429"
        },
        json={
            "session_id": session_id,
            "message": "Hello",
        },
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": "all providers unavailable"
    }

    # Failed requests must not appear in history.
    history_response = await client.get(
        f"/sessions/{session_id}/messages"
    )

    assert history_response.status_code == 404


# ============================================================
# 7. SUCCESSFUL CHAT IS PERSISTED
# ============================================================

@pytest.mark.asyncio
async def test_successful_chat_is_persisted(client):
    session_id = "pytest-persistence-test"

    fake_result = {
        "reply": "Mocked AI response",
        "model": "gemini/test-model",
        "input_tokens": 10,
        "output_tokens": 5,
        "key_id": "key_1",
        "fallback_attempts": 0,
        "resolution_source": "LIVE_INFERENCE",
    }

    # Mock Gemini so the automated test does not make
    # a real network/API request.
    with patch(
        "app.main.generate_response",
        new=AsyncMock(return_value=fake_result),
    ):
        response = await client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message": "Hello persistence",
            },
        )

    assert response.status_code == 200

    response_data = response.json()

    assert (
        response_data["reply"]
        == "Mocked AI response"
    )

    assert (
        response_data["metadata"]["resolution_source"]
        == "LIVE_INFERENCE"
    )

    # Verify SQLite history.
    history_response = await client.get(
        f"/sessions/{session_id}/messages"
    )

    assert history_response.status_code == 200

    messages = history_response.json()["messages"]

    assert len(messages) == 2

    assert messages[0]["role"] == "user"
    assert (
        messages[0]["content"]
        == "Hello persistence"
    )

    assert messages[1]["role"] == "assistant"
    assert (
        messages[1]["content"]
        == "Mocked AI response"
    )


# ============================================================
# 8. MULTI-TURN HISTORY IS SENT BACK TO THE LLM
# ============================================================

@pytest.mark.asyncio
async def test_multi_turn_history_sent_to_llm(
    client,
):
    session_id = "pytest-multiturn-test"

    first_result = {
        "reply": "I will remember blue.",
        "model": "gemini/test-model",
        "input_tokens": 10,
        "output_tokens": 5,
        "key_id": "key_1",
        "fallback_attempts": 0,
        "resolution_source": "LIVE_INFERENCE",
    }

    second_result = {
        "reply": "Your favorite color is blue.",
        "model": "gemini/test-model",
        "input_tokens": 20,
        "output_tokens": 7,
        "key_id": "key_1",
        "fallback_attempts": 0,
        "resolution_source": "LIVE_INFERENCE",
    }

    mocked_generate = AsyncMock(
        side_effect=[
            first_result,
            second_result,
        ]
    )

    with patch(
        "app.main.generate_response",
        new=mocked_generate,
    ):
        first_response = await client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message":
                    "My favorite color is blue.",
            },
        )

        second_response = await client.post(
            "/chat",
            json={
                "session_id": session_id,
                "message":
                    "What is my favorite color?",
            },
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    # generate_response() should have been called twice.
    assert mocked_generate.await_count == 2

    # Examine the messages passed to the second LLM call.
    second_call = mocked_generate.await_args_list[1]

    messages_sent = second_call.args[0]

    # Previous user message must be included.
    assert {
        "role": "user",
        "content": "My favorite color is blue.",
    } in messages_sent

    # Previous assistant response must also be included.
    assert {
        "role": "assistant",
        "content": "I will remember blue.",
    } in messages_sent

    # New user message should be last.
    assert messages_sent[-1] == {
        "role": "user",
        "content": "What is my favorite color?",
    }


# ============================================================
# 9. KEY_1 FAILURE -> KEY_2 FALLBACK
# ============================================================

@pytest.mark.asyncio
async def test_key_1_failure_falls_back_to_key_2():
    """
    Simulate key_1 returning 429.

    LiteLLM itself is mocked so key_2 succeeds without
    making a real Gemini API request.
    """

    from app.llm_service import generate_response

    fake_message = type(
        "FakeMessage",
        (),
        {
            "content": "Fallback worked"
        },
    )()

    fake_choice = type(
        "FakeChoice",
        (),
        {
            "message": fake_message
        },
    )()

    fake_usage = type(
        "FakeUsage",
        (),
        {
            "prompt_tokens": 10,
            "completion_tokens": 4,
        },
    )()

    fake_response = type(
        "FakeResponse",
        (),
        {
            "choices": [fake_choice],
            "usage": fake_usage,
            "_hidden_params": {},
        },
    )()

    with patch(
        "app.llm_service.litellm.acompletion",
        new=AsyncMock(
            return_value=fake_response
        ),
    ):
        result = await generate_response(
            [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ],
            simulated_failures={
                "key_1": 429
            },
        )

    assert result["reply"] == "Fallback worked"

    assert result["key_id"] == "key_2"

    assert result["fallback_attempts"] == 1

    assert (
        result["resolution_source"]
        == "LIVE_INFERENCE"
    )

    assert result["input_tokens"] == 10

    assert result["output_tokens"] == 4