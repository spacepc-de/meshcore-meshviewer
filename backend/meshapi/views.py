from rest_framework.response import Response
from rest_framework.views import APIView

from django.utils import timezone
from .services import (
    get_or_refresh_node_info,
    _run_info_command,
    _run_contacts_command,
    _run_contact_info_command,
)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({
            "status": "ok",
            "service": "backend",
        })


class MyNodeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        name = request.query_params.get("name", "JOST_DEV")
        # Optional: allow overriding max age via ?max_age=3600
        try:
            max_age = int(request.query_params.get("max_age", "3600"))
        except ValueError:
            max_age = 3600

        try:
            data, fetched_at = get_or_refresh_node_info(name=name, max_age_seconds=max_age)
        except Exception:
            # Fallback: run the command directly without DB caching
            data = _run_info_command(name=name)
            fetched_at = timezone.now()

        return Response({
            "name": name,
            "fetched_at": fetched_at,
            "data": data,
        })


class ContactsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        items = _run_contacts_command()
        return Response({
            "fetched_at": timezone.now(),
            "items": items,
        })


class ContactInfoView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        name = request.query_params.get("name")
        if not name:
            return Response({"detail": "Parameter 'name' ist erforderlich."}, status=400)
        data = _run_contact_info_command(name)
        return Response({
            "fetched_at": timezone.now(),
            "name": name,
            "data": data,
        })
