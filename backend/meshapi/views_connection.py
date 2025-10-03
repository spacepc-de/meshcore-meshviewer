from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .session import get_session


class ConnectionStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        s = get_session()
        connected = s.is_alive()
        return Response({
            "connected": bool(connected),
        })


class ConnectionReconnectView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        s = get_session()
        try:
            s.ensure_started()
            ok = s.is_alive()
            return Response({"ok": bool(ok), "connected": bool(ok)})
        except Exception as e:
            return Response({
                "ok": False,
                "connected": False,
                "detail": str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

