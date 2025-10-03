from django.apps import AppConfig


class MeshapiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "meshapi"

    def ready(self):  # pragma: no cover
        # Import signal handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
