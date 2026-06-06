from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8000
    node_env: str = "development"

    skip_auth: bool = True
    skip_workers: bool = True
    skip_web_push: bool = True

    jwks_uri: str
    jwt_audience: str = "ubicatec"
    jwt_issuer: str = "ubicatec-auth"

    service_bus_conn_string: str
    service_bus_queue: str = "rsvp-confirmations"
    service_bus_topic: str = "events"
    service_bus_subscription: str = "events.notifier"

    table_storage_conn_string: str
    notifications_table: str = "Notifications"
    push_subs_table: str = "PushSubs"

    vapid_public_key: str
    vapid_private_key: str
    vapid_subject: str = "mailto:ubicatec.notifs@gmail.com"

    apim_cert_thumbprint: str = ""
    applicationinsights_connection_string: str = ""

    class Config:
        env_file = ".env"


settings = Settings()