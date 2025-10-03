from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message
from .services import evaluate_automations_for_message


@receiver(post_save, sender=Message)
def run_automations_on_incoming(sender, instance: Message, created: bool, **kwargs):  # pragma: no cover - runtime hook
    try:
        if not created:
            return
        if instance.direction != "in":
            return
        name = instance.name or ""
        public_key = instance.public_key or None
        text = instance.text or ""
        # Fire and forget; errors are intentionally swallowed to not break message ingestion
        evaluate_automations_for_message(name=name, public_key=public_key, direction="in", text=text, dry_run=False)
    except Exception:
        # Avoid raising from signal
        pass

