from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import CollectorConfig, MQTTConfig

import socket
import threading

try:  # optional import; endpoint will error nicely if missing
    import paho.mqtt.client as mqtt  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    mqtt = None


class CollectorSettingsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        cfg = CollectorConfig.objects.order_by('-id').first()
        return Response({
            'interval_seconds': cfg.interval_seconds if cfg else 300,
            'enable_req_telemetry': bool(cfg.enable_req_telemetry) if cfg else False,
            'enable_req_status': bool(getattr(cfg, 'enable_req_status', True)) if cfg else True,
        })

    def post(self, request):
        return self._upsert(request)

    def put(self, request):
        return self._upsert(request)

    def patch(self, request):
        return self._upsert(request)

    def _upsert(self, request):
        try:
            interval = int(request.data.get('interval_seconds'))
        except Exception:
            return Response({'detail': 'interval_seconds muss eine Zahl sein.'}, status=status.HTTP_400_BAD_REQUEST)
        if interval < 0:
            return Response({'detail': 'interval_seconds darf nicht negativ sein.'}, status=status.HTTP_400_BAD_REQUEST)
        cfg = CollectorConfig.objects.order_by('-id').first()
        if not cfg:
            cfg = CollectorConfig.objects.create(interval_seconds=interval)
        else:
            cfg.interval_seconds = interval
        # Optional flag: enable_req_telemetry (keep previous if not provided)
        if 'enable_req_telemetry' in request.data:
            try:
                cfg.enable_req_telemetry = bool(request.data.get('enable_req_telemetry'))
            except Exception:
                pass
        # Optional flag: enable_req_status (keep previous if not provided)
        if 'enable_req_status' in request.data:
            try:
                cfg.enable_req_status = bool(request.data.get('enable_req_status'))
            except Exception:
                pass
        cfg.save()
        return Response({
            'interval_seconds': cfg.interval_seconds,
            'enable_req_telemetry': bool(cfg.enable_req_telemetry),
            'enable_req_status': bool(getattr(cfg, 'enable_req_status', True)),
        })


class MQTTSettingsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        cfg = MQTTConfig.objects.order_by('-id').first()
        if not cfg:
            return Response({
                'server': '',
                'port': 1883,
                'username': '',
                'password_set': False,
                'use_tls': False,
                'default_community': '',
            })
        return Response({
            'server': cfg.server or '',
            'port': cfg.port or 1883,
            'username': cfg.username or '',
            'password_set': bool(cfg.password),
            'use_tls': bool(cfg.use_tls),
            'default_community': cfg.default_community or '',
        })

    def post(self, request):
        return self._upsert(request)

    def put(self, request):
        return self._upsert(request)

    def patch(self, request):
        return self._upsert(request)

    def _upsert(self, request):
        data = request.data or {}
        # Validate and coerce
        server = (data.get('server') or '').strip()
        username = (data.get('username') or '').strip()
        default_community = (data.get('default_community') or '').strip()
        use_tls = bool(data.get('use_tls'))
        # Port
        try:
            port_raw = data.get('port', 1883)
            port = int(port_raw)
        except Exception:
            return Response({'detail': 'port muss eine Zahl sein.'}, status=status.HTTP_400_BAD_REQUEST)
        if not (0 < port < 65536):
            return Response({'detail': 'port muss zwischen 1 und 65535 liegen.'}, status=status.HTTP_400_BAD_REQUEST)

        cfg = MQTTConfig.objects.order_by('-id').first() or MQTTConfig()
        cfg.server = server
        cfg.port = port
        cfg.username = username
        cfg.use_tls = use_tls
        cfg.default_community = default_community

        # Password handling: if key present, set it (allow empty to clear). If absent, keep.
        if 'password' in data:
            cfg.password = (data.get('password') or '')

        cfg.save()

        return Response({
            'server': cfg.server or '',
            'port': cfg.port or 1883,
            'username': cfg.username or '',
            'password_set': bool(cfg.password),
            'use_tls': bool(cfg.use_tls),
            'default_community': cfg.default_community or '',
        })


class MQTTTestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if mqtt is None:
            return Response(
                {'detail': 'MQTT-Unterstützung ist nicht installiert (paho-mqtt fehlt).'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = request.data or {}

        # Load stored config to use password if not explicitly provided
        stored = MQTTConfig.objects.order_by('-id').first()

        server = (data.get('server') or (stored.server if stored else '') or '').strip()
        if not server:
            return Response({'detail': 'server darf nicht leer sein.'}, status=status.HTTP_400_BAD_REQUEST)

        # Port
        try:
            port_raw = data.get('port', stored.port if stored else 1883)
            port = int(port_raw)
        except Exception:
            return Response({'detail': 'port muss eine Zahl sein.'}, status=status.HTTP_400_BAD_REQUEST)
        if not (0 < port < 65536):
            return Response({'detail': 'port muss zwischen 1 und 65535 liegen.'}, status=status.HTTP_400_BAD_REQUEST)

        username = (data.get('username') if data.get('username') is not None else (stored.username if stored else '')) or ''
        username = str(username).strip()
        # Only use provided password if key present (allow empty to clear), else use stored password
        if 'password' in data:
            password = data.get('password') or ''
        else:
            password = (stored.password if stored else '')
        use_tls = bool(data.get('use_tls') if data.get('use_tls') is not None else (stored.use_tls if stored else False))

        # Attempt connection with short socket timeout and wait for CONNACK
        prev_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5.0)
        try:
            client = mqtt.Client(protocol=mqtt.MQTTv311)
            if username:
                client.username_pw_set(username, password or None)
            if use_tls:
                import ssl

                client.tls_set(tls_version=ssl.PROTOCOL_TLS)
                client.tls_insecure_set(False)

            conn_event = threading.Event()
            result = {'rc': None}

            def _on_connect(cl, userdata, flags, rc):  # rc: 0 success; non-zero failure
                result['rc'] = rc
                conn_event.set()

            client.on_connect = _on_connect

            # Start network loop and connect
            client.loop_start()
            client.connect(server, port, keepalive=10)

            # Wait up to 5 seconds for CONNACK
            if not conn_event.wait(timeout=5.0):
                return Response({'detail': 'Timeout beim Warten auf Broker-Antwort (CONNACK).'}, status=status.HTTP_400_BAD_REQUEST)

            rc = result['rc']
            if rc != 0:
                # Map common rc codes
                rc_map = {
                    1: 'Unzulässige Protokollversion',
                    2: 'Client-ID abgelehnt',
                    3: 'Server nicht verfügbar',
                    4: 'Falscher Benutzername oder Passwort',
                    5: 'Nicht autorisiert',
                }
                msg = rc_map.get(rc, f'Broker meldete Fehler (rc={rc}).')
                return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'ok': True, 'detail': 'Verbindung erfolgreich.'})
        except Exception as e:
            return Response({'detail': f'Verbindung fehlgeschlagen: {e.__class__.__name__}: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass
            socket.setdefaulttimeout(prev_timeout)
