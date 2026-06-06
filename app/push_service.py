import json
import structlog
from pywebpush import webpush, WebPushException

from app.config import settings
from app.table_client import get_push_subscriptions


log = structlog.get_logger()


async def send_push_to_user(email: str, data: dict):
    if settings.skip_web_push:
        return

    subscriptions = await get_push_subscriptions(email)

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps(data),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={
                    "sub": settings.vapid_subject
                }
            )
        except WebPushException as error:
            log.warning("web_push_failed", email=email, error=str(error))