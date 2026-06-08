from fastapi import APIRouter, Depends, HTTPException, Query, Body

from app.auth import require_auth
from app.config import settings
from app.table_client import (
    list_notifications,
    mark_notification_as_read,
    save_push_subscription,
    delete_push_subscription
)


router = APIRouter()

@router.get("")
@router.get("/")
async def get_notifications(
    unread: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(require_auth)
):
    email = user["email"]

    data = await list_notifications(
        email=email,
        unread=unread,
        limit=limit
    )

    return {
        "data": data,
        "limit": limit
    }


@router.get("/vapid-key")
async def get_vapid_key():
    return {
        "publicKey": settings.vapid_public_key
    }


@router.post("/subscribe")
async def subscribe(
    subscription: dict = Body(...),
    user=Depends(require_auth)
):
    email = user["email"]

    subscription_id = await save_push_subscription(
        email=email,
        subscription=subscription
    )

    return {
        "success": True,
        "subscriptionId": subscription_id
    }


@router.delete("/subscribe")
async def unsubscribe(
    payload: dict = Body(...),
    user=Depends(require_auth)
):
    email = user["email"]
    endpoint = payload.get("endpoint")

    if not endpoint:
        raise HTTPException(status_code=400, detail="endpoint requerido")

    deleted = await delete_push_subscription(
        email=email,
        endpoint=endpoint
    )

    return {
        "success": True,
        "deleted": deleted
    }


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user=Depends(require_auth)
):
    email = user["email"]

    updated = await mark_notification_as_read(
        email=email,
        notification_id=notification_id
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    return {
        "success": True
    }