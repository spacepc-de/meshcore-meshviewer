from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q

from .models import Message
from .models import Contact
from .services import send_chat_message


class MessagesListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        pk = request.query_params.get('public_key')
        name = request.query_params.get('name')
        try:
            limit = int(request.query_params.get('limit', '50'))
        except Exception:
            limit = 50
        qs = Message.objects.all()
        if pk and name:
            qs = qs.filter(Q(public_key=pk) | Q(name=name))
        elif pk:
            qs = qs.filter(public_key=pk)
        elif name:
            qs = qs.filter(name=name)
        qs = qs.order_by('-ts')[: max(1, min(limit, 500))]
        items = [
            {
                'name': m.name,
                'public_key': m.public_key,
                'direction': m.direction,
                'text': m.text,
                'ts': m.ts,
                'status': m.status,
                'client_id': m.client_id,
                'id': m.id,
            }
            for m in qs
        ]
        return Response({'fetched_at': timezone.now(), 'items': items})


class MessageSendView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.data or {}
        name = (payload.get('name') or '').strip()
        public_key = (payload.get('public_key') or '').strip()
        text = payload.get('text') or ''
        client_id = (payload.get('client_id') or '').strip() or None

        if not name and public_key:
            # Attempt to resolve name from public_key
            try:
                c = Contact.objects.filter(public_key=public_key).order_by('-last_seen').first()
                if c and c.name:
                    name = c.name
            except Exception:
                pass

        if not name:
            return Response({'error': 'name or public_key required'}, status=400)
        if not text or not str(text).strip():
            return Response({'error': 'text required'}, status=400)

        try:
            status = send_chat_message(name=name, text=str(text), client_id=client_id)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': f'failed to send: {e}'}, status=500)

        return Response({'ok': True, 'status': status, 'client_id': client_id})
