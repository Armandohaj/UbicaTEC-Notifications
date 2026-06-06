import asyncio
import json
import structlog

from azure.servicebus.aio import ServiceBusClient

from app.config import settings
from app.table_client import save_notification
from app.ws_manager import manager
from app.push_service import send_push_to_user


log = structlog.get_logger()


def parse_service_bus_message(message):
    raw = b"".join([part for part in message.body])
    return json.loads(raw.decode("utf-8"))


async def process_rsvp_message(body: dict):
    email = body["email"]
    title = body["title"]
    event_id = body["eventId"]
    date = body.get("date", "")

    notification_title = f"RSVP confirmado: {title}"
    notification_body = f"Tu registro para {title} el {date} fue exitoso."

    notification_id = await save_notification(
        email=email,
        title=notification_title,
        body=notification_body,
        kind="rsvp_confirmed",
        event_id=event_id
    )

    notification = {
        "id": notification_id,
        "kind": "rsvp_confirmed",
        "title": notification_title,
        "body": notification_body,
        "eventId": event_id,
        "read": False
    }

    await manager.send_to_user(email, notification)
    await send_push_to_user(email, notification)


async def process_event_created_message(body: dict):
    title = body["title"]
    event_id = body["eventId"]
    date = body.get("date", "")
    created_by = body.get("createdBy", "sistema")

    # En Fase II todavía no tenemos lista real de usuarios activos.
    # Por eso el broadcast se manda por WebSocket a usuarios conectados.
    notification = {
        "id": body.get("messageId", event_id),
        "kind": "event_created",
        "title": f"Nuevo evento: {title}",
        "body": f"Se publicó un nuevo evento para la fecha {date}.",
        "eventId": event_id,
        "createdBy": created_by,
        "read": False
    }

    await manager.broadcast(notification)


async def process_rsvp_queue():
    async with ServiceBusClient.from_connection_string(
        settings.service_bus_conn_string
    ) as service_bus_client:
        receiver = service_bus_client.get_queue_receiver(
            queue_name=settings.service_bus_queue
        )

        async with receiver:
            async for message in receiver:
                try:
                    body = parse_service_bus_message(message)
                    await process_rsvp_message(body)
                    await receiver.complete_message(message)
                    log.info("rsvp_message_completed", event_id=body.get("eventId"))
                except Exception as error:
                    log.error("rsvp_worker_error", error=str(error))
                    await receiver.abandon_message(message)


async def process_events_topic():
    async with ServiceBusClient.from_connection_string(
        settings.service_bus_conn_string
    ) as service_bus_client:
        receiver = service_bus_client.get_subscription_receiver(
            topic_name=settings.service_bus_topic,
            subscription_name=settings.service_bus_subscription
        )

        async with receiver:
            async for message in receiver:
                try:
                    body = parse_service_bus_message(message)
                    await process_event_created_message(body)
                    await receiver.complete_message(message)
                    log.info("event_created_message_completed", event_id=body.get("eventId"))
                except Exception as error:
                    log.error("events_worker_error", error=str(error))
                    await receiver.abandon_message(message)


async def start_workers():
    if settings.skip_workers:
        log.info("workers_skipped")
        return []

    tasks = [
        asyncio.create_task(process_rsvp_queue()),
        asyncio.create_task(process_events_topic())
    ]

    log.info("workers_started")

    return tasks


async def stop_workers(tasks):
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)