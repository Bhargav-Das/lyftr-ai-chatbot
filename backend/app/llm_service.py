from typing import Any

import litellm
from litellm import Cache

from app.config import settings


# LiteLLM built-in in-memory cache.
litellm.cache = Cache(type="local")

ALLOWED_SIMULATED_STATUSES = {
    429,
    500,
    502,
    503,
}


class SimulatedProviderError(Exception):
    def __init__(
        self,
        key_id: str,
        status_code: int,
    ):
        self.key_id = key_id
        self.status_code = status_code

        super().__init__(
            f"Simulated provider failure: "
            f"{key_id}={status_code}"
        )


def parse_failure_simulation(
    header_value: str | None,
) -> dict[str, int]:

    if not settings.enable_failure_simulation:
        return {}

    if not header_value:
        return {}

    failures: dict[str, int] = {}

    for item in header_value.split(","):
        item = item.strip()

        if not item or "=" not in item:
            continue

        key_id, status_text = item.split(
            "=",
            1,
        )

        key_id = key_id.strip()
        status_text = status_text.strip()

        try:
            status_code = int(status_text)
        except ValueError:
            continue

        if status_code not in ALLOWED_SIMULATED_STATUSES:
            continue

        failures[key_id] = status_code

    return failures


def response_is_cached(
    response: Any,
) -> bool:
    """
    Detect LiteLLM cache-hit metadata without depending
    on a single response representation.
    """

    hidden_params = getattr(
        response,
        "_hidden_params",
        {},
    ) or {}

    return bool(
        hidden_params.get("cache_hit")
        or hidden_params.get("cached_response")
    )


async def generate_response(
    messages: list[dict[str, str]],
    simulated_failures: dict[str, int] | None = None,
) -> dict[str, Any]:

    api_keys = settings.api_keys

    if not api_keys:
        raise RuntimeError(
            "No LLM API keys configured"
        )

    simulated_failures = (
        simulated_failures or {}
    )

    last_exception: Exception | None = None

    for index, api_key in enumerate(api_keys):
        key_id = f"key_{index + 1}"

        try:
            print(
                f"Attempting inference with {key_id}"
            )

            simulated_status = None

            if "*" in simulated_failures:
                simulated_status = (
                    simulated_failures["*"]
                )

            elif key_id in simulated_failures:
                simulated_status = (
                    simulated_failures[key_id]
                )

            if simulated_status is not None:
                print(
                    f"Simulating {simulated_status} "
                    f"for {key_id}"
                )

                raise SimulatedProviderError(
                    key_id=key_id,
                    status_code=simulated_status,
                )

            response = await litellm.acompletion(
                model=settings.llm_model,
                messages=messages,
                api_key=api_key,
                caching=True,
                timeout=30,
            )

            reply = (
                response
                .choices[0]
                .message
                .content
            )

            if not reply:
                raise RuntimeError(
                    "LLM returned an empty response"
                )

            usage = getattr(
                response,
                "usage",
                None,
            )

            input_tokens = (
                getattr(
                    usage,
                    "prompt_tokens",
                    0,
                )
                if usage is not None
                else 0
            )

            output_tokens = (
                getattr(
                    usage,
                    "completion_tokens",
                    0,
                )
                if usage is not None
                else 0
            )

            cache_hit = response_is_cached(
                response
            )

            if cache_hit:
                print("LiteLLM cache hit")

                return {
                    "reply": reply,
                    "model": settings.llm_model,
                    "input_tokens": int(
                        input_tokens or 0
                    ),
                    "output_tokens": int(
                        output_tokens or 0
                    ),
                    "key_id": None,
                    "fallback_attempts": 0,
                    "resolution_source": "LLM_CACHE",
                }

            print(
                f"Inference succeeded with {key_id}"
            )

            return {
                "reply": reply,
                "model": settings.llm_model,
                "input_tokens": int(
                    input_tokens or 0
                ),
                "output_tokens": int(
                    output_tokens or 0
                ),
                "key_id": key_id,
                "fallback_attempts": index,
                "resolution_source": "LIVE_INFERENCE",
            }

        except Exception as exc:
            last_exception = exc

            print(
                f"{key_id} failed: "
                f"{type(exc).__name__}"
            )

            continue

    if last_exception is not None:
        raise last_exception

    raise RuntimeError(
        "All LLM API keys failed"
    )