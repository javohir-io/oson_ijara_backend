from fastapi import WebSocket


class ConnectionManager:
    """Tracks which users currently have an open chat WebSocket, so a
    message can be pushed to them live if they're online. Messages are
    always persisted to the database regardless of whether the recipient
    is connected — this is just the "push it now if you can" layer on top.
    """

    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, payload: dict) -> bool:
        """Returns True if the user was online and the message was pushed."""
        sockets = self._connections.get(user_id)
        if not sockets:
            return False
        for ws in list(sockets):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)
        return True


manager = ConnectionManager()
