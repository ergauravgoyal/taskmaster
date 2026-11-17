import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class NotificationManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(user_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(user_id, None)

    async def publish(self, user_id: int, notification: dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections.get(user_id, ()))
        failed: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(notification)
            except (WebSocketDisconnect, RuntimeError):
                failed.append(websocket)
        for websocket in failed:
            await self.disconnect(user_id, websocket)


manager = NotificationManager()
