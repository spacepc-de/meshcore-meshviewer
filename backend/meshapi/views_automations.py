from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import AutomationRule
from .services import evaluate_automations_for_message


class AutomationsListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        qs = AutomationRule.objects.all().order_by("-enabled", "-priority", "name")
        items = [serialize_rule(r) for r in qs]
        return Response({"fetched_at": timezone.now(), "items": items})

    def post(self, request):
        data = request.data or {}
        ok, payload_or_err = validate_and_hydrate_rule_payload(data)
        if not ok:
            return Response({"detail": payload_or_err}, status=status.HTTP_400_BAD_REQUEST)
        rule = AutomationRule.objects.create(**payload_or_err)
        return Response(serialize_rule(rule), status=status.HTTP_201_CREATED)


class AutomationDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk: int):
        rule = get_object_or_404(AutomationRule, pk=pk)
        return Response(serialize_rule(rule))

    def delete(self, request, pk: int):
        rule = get_object_or_404(AutomationRule, pk=pk)
        rule.delete()
        return Response({"ok": True})

    def put(self, request, pk: int):
        return self._update(request, pk)

    def patch(self, request, pk: int):
        return self._update(request, pk)

    def _update(self, request, pk: int):
        rule = get_object_or_404(AutomationRule, pk=pk)
        data = request.data or {}
        ok, payload_or_err = validate_and_hydrate_rule_payload(data, partial=True)
        if not ok:
            return Response({"detail": payload_or_err}, status=status.HTTP_400_BAD_REQUEST)
        for k, v in payload_or_err.items():
            setattr(rule, k, v)
        rule.save()
        return Response(serialize_rule(rule))


class AutomationsTestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        data = request.data or {}
        name = (data.get("name") or "").strip()
        public_key = (data.get("public_key") or "").strip() or None
        text = (data.get("text") or "").strip()
        dry_run = True if data.get("dry_run") is None else bool(data.get("dry_run"))
        if not text:
            return Response({"detail": "text darf nicht leer sein."}, status=status.HTTP_400_BAD_REQUEST)
        res = evaluate_automations_for_message(name=name, public_key=public_key, direction="in", text=text, dry_run=dry_run)
        return Response({"ok": True, "results": res, "dry_run": dry_run})


def serialize_rule(r: AutomationRule) -> dict:
    return {
        "id": r.id,
        "enabled": r.enabled,
        "name": r.name,
        "description": r.description,
        "match_type": r.match_type,
        "pattern": r.pattern,
        "case_sensitive": r.case_sensitive,
        "only_incoming": r.only_incoming,
        "from_name": r.from_name,
        "from_public_key": r.from_public_key,
        "action_type": r.action_type,
        "response_text": r.response_text,
        "mqtt_topic": r.mqtt_topic,
        "mqtt_payload": r.mqtt_payload,
        "priority": r.priority,
        "stop_processing": r.stop_processing,
        "cooldown_seconds": r.cooldown_seconds,
        "last_triggered_at": r.last_triggered_at,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def validate_and_hydrate_rule_payload(data: dict, partial: bool = False):
    try:
        payload = {}
        if not partial or "enabled" in data:
            payload["enabled"] = bool(data.get("enabled", True))
        if not partial or "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return False, "name darf nicht leer sein."
            payload["name"] = name
        if not partial or "description" in data:
            payload["description"] = (data.get("description") or "")

        if not partial or "match_type" in data:
            mt = (data.get("match_type") or "prefix").strip()
            if mt not in {"equals", "prefix", "contains", "regex"}:
                return False, "match_type muss one of equals|prefix|contains|regex sein."
            payload["match_type"] = mt
        if not partial or "pattern" in data:
            pattern = (data.get("pattern") or "").strip()
            if not pattern:
                return False, "pattern darf nicht leer sein."
            payload["pattern"] = pattern
        if not partial or "case_sensitive" in data:
            payload["case_sensitive"] = bool(data.get("case_sensitive", False))
        if not partial or "only_incoming" in data:
            payload["only_incoming"] = bool(data.get("only_incoming", True))

        if not partial or "from_name" in data:
            payload["from_name"] = (data.get("from_name") or "").strip()
        if not partial or "from_public_key" in data:
            payload["from_public_key"] = (data.get("from_public_key") or "").strip()

        if not partial or "action_type" in data:
            at = (data.get("action_type") or "").strip()
            if at not in {"autoresponse", "mqtt"}:
                return False, "action_type muss one of autoresponse|mqtt sein."
            payload["action_type"] = at
        if not partial or "response_text" in data:
            payload["response_text"] = data.get("response_text") or ""
        if not partial or "mqtt_topic" in data:
            payload["mqtt_topic"] = (data.get("mqtt_topic") or "")
        if not partial or "mqtt_payload" in data:
            payload["mqtt_payload"] = (data.get("mqtt_payload") or "")

        if not partial or "priority" in data:
            try:
                payload["priority"] = int(data.get("priority", 0))
            except Exception:
                return False, "priority muss eine Zahl sein."
        if not partial or "stop_processing" in data:
            payload["stop_processing"] = bool(data.get("stop_processing", True))
        if not partial or "cooldown_seconds" in data:
            try:
                cd = int(data.get("cooldown_seconds", 0))
            except Exception:
                return False, "cooldown_seconds muss eine Zahl sein."
            if cd < 0:
                return False, "cooldown_seconds darf nicht negativ sein."
            payload["cooldown_seconds"] = cd

        return True, payload
    except Exception as e:
        return False, f"ungültige Daten: {e}"

