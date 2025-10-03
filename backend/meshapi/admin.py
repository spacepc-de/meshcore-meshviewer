from django.contrib import admin
from .models import Contact, ContactTelemetry, Message, CollectorConfig, NodeInfo, AutomationRule


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "public_key", "first_seen", "last_seen")
    search_fields = ("name", "public_key")
    list_filter = ("last_seen",)
    ordering = ("-last_seen",)


@admin.register(ContactTelemetry)
class ContactTelemetryAdmin(admin.ModelAdmin):
    list_display = (
        "contact",
        "adv_name",
        "last_advert",
        "adv_lat",
        "adv_lon",
        "fetched_at",
    )
    search_fields = ("contact__name", "contact__public_key", "adv_name")
    list_filter = ("fetched_at",)
    ordering = ("-fetched_at",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("ts", "direction", "name", "public_key", "short_text")
    search_fields = ("name", "public_key", "text")
    list_filter = ("direction", "ts")
    ordering = ("-ts",)

    def short_text(self, obj):  # pragma: no cover
        t = obj.text or ""
        return (t[:80] + "…") if len(t) > 80 else t
    short_text.short_description = "Text"


@admin.register(CollectorConfig)
class CollectorConfigAdmin(admin.ModelAdmin):
    list_display = ("interval_seconds", "updated_at")


@admin.register(NodeInfo)
class NodeInfoAdmin(admin.ModelAdmin):
    list_display = ("name", "fetched_at")
    search_fields = ("name",)
    list_filter = ("fetched_at",)
    ordering = ("-fetched_at",)


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ("enabled", "name", "match_type", "pattern", "action_type", "priority", "last_triggered_at")
    search_fields = ("name", "pattern", "description")
    list_filter = ("enabled", "match_type", "action_type")
    ordering = ("-enabled", "-priority", "name")
