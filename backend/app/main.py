from contextlib import asynccontextmanager
from time import perf_counter


from fastapi import (
    FastAPI,
    Header,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import (
    add_message,
    check_database,
    get_session_messages,
    init_db,
)
from app.llm_service import (
    generate_response,
    parse_failure_simulation,
)
from app.schemas import (
    ChatMetadata,
    ChatRequest,
    ChatResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)


origins = [
    origin.strip()
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    database_ok = await check_database()

    if not database_ok:
        raise HTTPException(
            status_code=503,
            detail="database unavailable",
        )

    return {
        "status": "ok",
        "keys_configured": len(
            settings.api_keys
        ),
        "cache_enabled": True,
    }


@app.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
    x_simulate_failure: str | None = Header(
        default=None,
        alias="X-Simulate-Failure",
    ),
):
    start_time = perf_counter()

    simulated_failures = (
        parse_failure_simulation(
            x_simulate_failure
        )
    )

    # Load existing conversation.
    history = await get_session_messages(
        request.session_id
    )

    system_prompt = (
        request.system_prompt
        or settings.default_system_prompt
    )

    # Full message list sent to the LLM.
    llm_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    # Add previous conversation.
    for message in history:
        llm_messages.append(
            {
                "role": message["role"],
                "content": message["content"],
            }
        )

    # Add current message.
    llm_messages.append(
        {
            "role": "user",
            "content": request.message,
        }
    )

    try:
        result = await generate_response(
            llm_messages,
            simulated_failures=simulated_failures,
        )

    except Exception as exc:
        # Local debugging only.
        # API clients still receive a safe error.
        print(
            "\nLLM ERROR TYPE: "
            f"{type(exc).__name__}"
        )

        print(
            f"LLM ERROR: {exc}\n"
        )

        raise HTTPException(
            status_code=503,
            detail="all providers unavailable",
        )

    latency_ms = int(
        (perf_counter() - start_time) * 1000
    )

    metadata = ChatMetadata(
        resolution_source=result["resolution_source"],
        model=result["model"],
        latency_ms=latency_ms,
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        key_id=result["key_id"],
        fallback_attempts=result[
            "fallback_attempts"
        ],
    )

    # IMPORTANT:
    # Store only after successful inference.
    await add_message(
        session_id=request.session_id,
        role="user",
        content=request.message,
    )

    await add_message(
        session_id=request.session_id,
        role="assistant",
        content=result["reply"],
        metadata=metadata.model_dump(),
    )

    return ChatResponse(
        session_id=request.session_id,
        reply=result["reply"],
        metadata=metadata,
    )


@app.get(
    "/sessions/{session_id}/messages"
)
async def session_messages(
    session_id: str,
):
    messages = await get_session_messages(
        session_id
    )

    if not messages:
        raise HTTPException(
            status_code=404,
            detail="session not found",
        )

    return {
        "session_id": session_id,
        "messages": messages,
    }