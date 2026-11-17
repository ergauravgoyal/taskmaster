import json
from typing import Any

from app.realtime import manager


async def create_notification(
    conn: Any,
    user_id: int,
    event_type: str,
    payload: dict[str, Any],
    task_id: int | None = None,
) -> None:
    row = await conn.fetchrow(
        """
        INSERT INTO notifications(user_id,task_id,event_type,payload)
        VALUES($1,$2,$3,$4::jsonb)
        RETURNING id,user_id,task_id,event_type,payload,read_at,created_at
        """,
        user_id, task_id, event_type, json.dumps(payload),
    )
    await manager.publish(user_id, dict(row))
