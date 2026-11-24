import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.config import settings


def get_database_path() -> str:
    prefix = "sqlite:///"

    if not settings.database_url.startswith(prefix):
        raise ValueError(
            "DATABASE_URL must be a SQLite URL"
        )

    return settings.database_url[len(prefix):]


async def init_db() -> None:
    database_path = get_database_path()

    async with aiosqlite.connect(
        database_path
    ) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_messages_session_id
            ON messages(session_id)
            """
        )

        await db.commit()


async def check_database() -> bool:
    try:
        database_path = get_database_path()

        async with aiosqlite.connect(
            database_path
        ) as db:
            await db.execute("SELECT 1")

        return True

    except Exception:
        return False


async def add_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    database_path = get_database_path()

    metadata_json = (
        json.dumps(metadata)
        if metadata is not None
        else None
    )

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    async with aiosqlite.connect(
        database_path
    ) as db:
        await db.execute(
            """
            INSERT INTO messages (
                session_id,
                role,
                content,
                metadata,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                content,
                metadata_json,
                created_at,
            ),
        )

        await db.commit()


async def get_session_messages(
    session_id: str,
) -> list[dict[str, Any]]:
    database_path = get_database_path()

    async with aiosqlite.connect(
        database_path
    ) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            """
            SELECT role, content, metadata
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )

        rows = await cursor.fetchall()

    messages: list[dict[str, Any]] = []

    for row in rows:
        message: dict[str, Any] = {
            "role": row["role"],
            "content": row["content"],
        }

        if row["metadata"] is not None:
            message["metadata"] = json.loads(
                row["metadata"]
            )

        messages.append(message)

    return messages