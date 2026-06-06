from fastapi import WebSocket
from typing import Dict, List


class WSManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, email: str):
        await websocket.accept()
        self.connections.setdefault(email, []).append(websocket)

    def disconnect(self, websocket: WebSocket, email: str):
        connections = self.connections.get(email, [])

        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self.connections.pop(email, None)

    async def send_to_user(self, email: str, data: dict):
        connections = list(self.connections.get(email, []))

        for websocket in connections:
            try:
                await websocket.send_json(data)
            except Exception:
                self.disconnect(websocket, email)

    async def broadcast(self, data: dict):
        for email in list(self.connections.keys()):
            await self.send_to_user(email, data)


manager = WSManager()