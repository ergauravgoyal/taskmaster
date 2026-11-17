from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
import jwt

from app.db import connection
from app.deps import current_user
from app.models import NotificationResponse
from app.realtime import manager
from app.security import decode_token

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(default=False),
    user=Depends(current_user),
):
    query = """
        SELECT id,user_id,task_id,event_type,payload,read_at,created_at
        FROM notifications
        WHERE user_id=$1
    """
    if unread_only:
        query += " AND read_at IS NULL"
    query += " ORDER BY created_at DESC LIMIT 100"
    async with connection() as conn:
        rows = await conn.fetch(query, user[0])
    return [dict(row) for row in rows]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(notification_id: int, user=Depends(current_user)):
    async with connection() as conn:
        row = await conn.fetchrow(
            """
            UPDATE notifications SET read_at=COALESCE(read_at, now())
            WHERE id=$1 AND user_id=$2
            RETURNING id,user_id,task_id,event_type,payload,read_at,created_at
            """,
            notification_id, user[0],
        )
    if not row:
        raise HTTPException(404, "Notification not found")
    return dict(row)


async def authenticate_websocket(websocket: WebSocket) -> int | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    try:
        user_id, token_id = decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    async with connection() as conn:
        return await conn.fetchval(
            """
            SELECT user_id FROM sessions
            WHERE user_id=$1 AND token_id=$2 AND revoked_at IS NULL AND expires_at > now()
            """,
            user_id, token_id,
        )


@router.websocket("/ws")
async def notifications_websocket(websocket: WebSocket):
    user_id = await authenticate_websocket(websocket)
    if user_id is None:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(user_id, websocket)
