from azure.monitor.opentelemetry import configure_azure_monitor

from app.config import settings


def setup_monitoring():
    connection_string = settings.applicationinsights_connection_string

    if not connection_string or connection_string == "example":
        print("Application Insights no configurado")
        print(f"Valor leído: {connection_string}")
        return

    configure_azure_monitor(
        connection_string=connection_string
    )

    print("Application Insights configurado")