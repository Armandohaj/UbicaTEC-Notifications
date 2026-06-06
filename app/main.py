from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query

from app.auth import verify_token_ws
from app.routes.notifications import router as notifications_router
from app.table_client import ensure_tables
from app.worker import start_workers, stop_workers
from app.ws_manager import manager


worker_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_tasks

    await ensure_tables()
    worker_tasks = await start_workers()

    yield

    await stop_workers(worker_tasks)


app = FastAPI(
    title="UbicaTEC Notifications Service",
    lifespan=lifespan
)

app.include_router(
    notifications_router,
    prefix="/v1/notifications",
    tags=["notifications"]
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "notifications"
    }


@app.websocket("/v1/notifications/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(default="")
):
    payload = await verify_token_ws(token)

    if not payload:
        await websocket.close(code=4001)
        return

    email = payload["email"]

    await manager.connect(websocket, email)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, email)