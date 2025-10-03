from django.urls import path
from .views import HealthView, MyNodeView, ContactsView, ContactInfoView
from .views_contacts import ContactsLatestView
from .views_messages import MessagesListView, MessageSendView
from .views_settings import CollectorSettingsView, MQTTSettingsView, MQTTTestView
from .views_connection import ConnectionStatusView, ConnectionReconnectView
from .views_automations import AutomationsListView, AutomationDetailView, AutomationsTestView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("my-node/", MyNodeView.as_view(), name="my-node"),
    path("contacts/", ContactsView.as_view(), name="contacts"),
    path("contact-info/", ContactInfoView.as_view(), name="contact-info"),
    path("contacts/latest/", ContactsLatestView.as_view(), name="contacts-latest"),
    path("settings/collector/", CollectorSettingsView.as_view(), name="collector-settings"),
    path("settings/mqtt/", MQTTSettingsView.as_view(), name="mqtt-settings"),
    path("settings/mqtt/test/", MQTTTestView.as_view(), name="mqtt-test"),
    path("messages/", MessagesListView.as_view(), name="messages-list"),
    path("messages/send/", MessageSendView.as_view(), name="messages-send"),
    path("automations/", AutomationsListView.as_view(), name="automations-list"),
    path("automations/test/", AutomationsTestView.as_view(), name="automations-test"),
    path("automations/<int:pk>/", AutomationDetailView.as_view(), name="automations-detail"),
    # Connection/session status
    path("connection/status/", ConnectionStatusView.as_view(), name="connection-status"),
    path("connection/reconnect/", ConnectionReconnectView.as_view(), name="connection-reconnect"),
]
