from django.db import models
from django.utils import timezone


class NodeInfo(models.Model):
    name = models.CharField(max_length=128, db_index=True)
    data = models.JSONField()
    fetched_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["name", "fetched_at"]),
        ]
        ordering = ["-fetched_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} @ {self.fetched_at.isoformat()}"


class Contact(models.Model):
    """A unique contact in the mesh, identified by public_key."""
    public_key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128, blank=True, default="")
    first_seen = models.DateTimeField(default=timezone.now, db_index=True)
    last_seen = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["public_key"]),
            models.Index(fields=["last_seen"]),
        ]
        ordering = ["-last_seen"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name or 'Contact'} ({self.public_key[:8]}…)"


class ContactTelemetry(models.Model):
    """Time-series telemetry for a contact (one row per fetch)."""
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="telemetry")
    fetched_at = models.DateTimeField(default=timezone.now, db_index=True)

    adv_name = models.CharField(max_length=128, blank=True, default="")
    last_advert = models.BigIntegerField(null=True, blank=True)
    adv_lat = models.FloatField(null=True, blank=True)
    adv_lon = models.FloatField(null=True, blank=True)
    # Link quality (if available)
    rssi = models.IntegerField(null=True, blank=True)
    snr = models.FloatField(null=True, blank=True)
    # Battery information
    battery_mv = models.IntegerField(null=True, blank=True)
    battery_percent = models.FloatField(null=True, blank=True)
    type = models.IntegerField(null=True, blank=True)
    flags = models.IntegerField(null=True, blank=True)
    out_path_len = models.IntegerField(null=True, blank=True)
    out_path = models.TextField(blank=True, default="")
    lastmod = models.BigIntegerField(null=True, blank=True)

    raw = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["contact", "fetched_at"]),
        ]
        ordering = ["-fetched_at"]


class CollectorConfig(models.Model):
    """Configuration for background contact telemetry collector."""
    updated_at = models.DateTimeField(auto_now=True)
    interval_seconds = models.IntegerField(default=300)  # default 5 minutes
    enable_req_telemetry = models.BooleanField(default=False)
    # New: allow disabling req_status calls from collector
    enable_req_status = models.BooleanField(default=True)

    def __str__(self) -> str:  # pragma: no cover
        mode_tel = "telemetry:on" if self.enable_req_telemetry else "telemetry:off"
        mode_stat = "status:on" if self.enable_req_status else "status:off"
        return f"Collector every {self.interval_seconds}s ({mode_tel}, {mode_stat})"


class MQTTConfig(models.Model):
    """Configuration for MQTT broker connection."""
    updated_at = models.DateTimeField(auto_now=True)
    server = models.CharField(max_length=255, blank=True, default="")
    port = models.IntegerField(default=1883)
    username = models.CharField(max_length=255, blank=True, default="")
    password = models.CharField(max_length=255, blank=True, default="")
    use_tls = models.BooleanField(default=False)
    default_community = models.CharField(max_length=255, blank=True, default="")

    def __str__(self) -> str:  # pragma: no cover
        scheme = "mqtts" if self.use_tls else "mqtt"
        auth = f"{self.username}@" if self.username else ""
        host = self.server or "<unset>"
        return f"{scheme}://{auth}{host}:{self.port}"


class Message(models.Model):
    """Incoming/outgoing chat messages parsed from the device console."""
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name="messages")
    name = models.CharField(max_length=128, blank=True, default="")
    public_key = models.CharField(max_length=64, null=True, blank=True)
    direction = models.CharField(max_length=3, choices=(("in", "in"), ("out", "out")))
    text = models.TextField()
    ts = models.DateTimeField(default=timezone.now, db_index=True)
    raw = models.TextField(blank=True, default="")
    # New: client-provided correlation ID for outgoing messages and a lightweight delivery status
    client_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        choices=(("sending", "sending"), ("sent", "sent"), ("delivered", "delivered"), ("failed", "failed")),
    )

    class Meta:
        indexes = [
            models.Index(fields=["ts"]),
            models.Index(fields=["public_key"]),
            models.Index(fields=["client_id"]),
        ]
        ordering = ["-ts"]


class AutomationRule(models.Model):
    """User-defined automations that react to message text and trigger actions.

    A rule matches incoming messages by simple pattern types and triggers either
    an autoresponse or an MQTT publish (or both in future iterations).
    """

    MATCH_EQUALS = "equals"
    MATCH_PREFIX = "prefix"
    MATCH_CONTAINS = "contains"
    MATCH_REGEX = "regex"
    MATCH_CHOICES = (
        (MATCH_EQUALS, "equals"),
        (MATCH_PREFIX, "prefix"),
        (MATCH_CONTAINS, "contains"),
        (MATCH_REGEX, "regex"),
    )

    ACTION_AUTORESPONSE = "autoresponse"
    ACTION_MQTT = "mqtt"
    ACTION_CHOICES = (
        (ACTION_AUTORESPONSE, "autoresponse"),
        (ACTION_MQTT, "mqtt"),
    )

    enabled = models.BooleanField(default=True, db_index=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")

    # Matching
    match_type = models.CharField(max_length=16, choices=MATCH_CHOICES, default=MATCH_PREFIX)
    pattern = models.CharField(max_length=256)
    case_sensitive = models.BooleanField(default=False)
    only_incoming = models.BooleanField(default=True)

    # Optional source filters
    from_name = models.CharField(max_length=128, blank=True, default="")
    from_public_key = models.CharField(max_length=64, blank=True, default="")

    # Action
    action_type = models.CharField(max_length=32, choices=ACTION_CHOICES)
    response_text = models.TextField(blank=True, default="")
    mqtt_topic = models.CharField(max_length=255, blank=True, default="")
    mqtt_payload = models.TextField(blank=True, default="")

    # Execution control
    priority = models.IntegerField(default=0, db_index=True)
    stop_processing = models.BooleanField(default=True)
    cooldown_seconds = models.IntegerField(default=0)  # 0 disables cooldown
    last_triggered_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["enabled", "priority"]),
        ]
        ordering = ["-enabled", "-priority", "name"]

    def __str__(self) -> str:  # pragma: no cover
        return f"[{('on' if self.enabled else 'off')}] {self.name} -> {self.action_type}"
