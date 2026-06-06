from datetime import datetime, timezone
from hashlib import sha256
from typing import List, Optional

from azure.data.tables.aio import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError
import ulid

from app.config import settings


_service_client = None


def get_table_service_client():
    global _service_client

    if _service_client is None:
        _service_client = TableServiceClient.from_connection_string(
            conn_str=settings.table_storage_conn_string
        )

    return _service_client


async def ensure_tables():
    client = get_table_service_client()

    await client.create_table_if_not_exists(settings.notifications_table)
    await client.create_table_if_not_exists(settings.push_subs_table)


async def save_notification(
    email: str,
    title: str,
    body: str,
    kind: str,
    event_id: Optional[str] = None
):
    notification_id = str(ulid.new())
    created_at = datetime.now(timezone.utc).isoformat()

    entity = {
        "PartitionKey": email,
        "RowKey": notification_id,
        "title": title,
        "body": body,
        "kind": kind,
        "eventId": event_id or "",
        "read": False,
        "createdAt": created_at
    }

    client = get_table_service_client()
    table = client.get_table_client(settings.notifications_table)

    await table.create_entity(entity=entity)

    return notification_id


async def list_notifications(email: str, unread: bool = False, limit: int = 20):
    client = get_table_service_client()
    table = client.get_table_client(settings.notifications_table)

    query = "PartitionKey eq @email"
    parameters = {
        "email": email
    }

    if unread:
        query += " and read eq @read"
        parameters["read"] = False

    results = []

    async for entity in table.query_entities(
        query_filter=query,
        parameters=parameters
    ):
        results.append({
            "id": entity["RowKey"],
            "title": entity.get("title", ""),
            "body": entity.get("body", ""),
            "kind": entity.get("kind", ""),
            "eventId": entity.get("eventId", ""),
            "read": entity.get("read", False),
            "createdAt": entity.get("createdAt", "")
        })

    results.sort(key=lambda item: item["createdAt"], reverse=True)

    return results[:limit]


async def mark_notification_as_read(email: str, notification_id: str):
    client = get_table_service_client()
    table = client.get_table_client(settings.notifications_table)

    try:
        entity = await table.get_entity(
            partition_key=email,
            row_key=notification_id
        )
    except ResourceNotFoundError:
        return False

    entity["read"] = True

    await table.update_entity(entity=entity, mode="merge")

    return True


def hash_endpoint(endpoint: str):
    return sha256(endpoint.encode("utf-8")).hexdigest()


async def save_push_subscription(email: str, subscription: dict):
    endpoint = subscription.get("endpoint")

    if not endpoint:
        return None

    keys = subscription.get("keys", {})

    entity = {
        "PartitionKey": email,
        "RowKey": hash_endpoint(endpoint),
        "endpoint": endpoint,
        "p256dh": keys.get("p256dh", ""),
        "auth": keys.get("auth", "")
    }

    client = get_table_service_client()
    table = client.get_table_client(settings.push_subs_table)

    await table.upsert_entity(entity=entity, mode="merge")

    return entity["RowKey"]


async def delete_push_subscription(email: str, endpoint: str):
    client = get_table_service_client()
    table = client.get_table_client(settings.push_subs_table)

    row_key = hash_endpoint(endpoint)

    try:
        await table.delete_entity(partition_key=email, row_key=row_key)
        return True
    except ResourceNotFoundError:
        return False


async def get_push_subscriptions(email: str) -> List[dict]:
    client = get_table_service_client()
    table = client.get_table_client(settings.push_subs_table)

    query = "PartitionKey eq @email"
    parameters = {
        "email": email
    }

    subscriptions = []

    async for entity in table.query_entities(
        query_filter=query,
        parameters=parameters
    ):
        subscriptions.append({
            "endpoint": entity.get("endpoint", ""),
            "keys": {
                "p256dh": entity.get("p256dh", ""),
                "auth": entity.get("auth", "")
            }
        })

    return subscriptions