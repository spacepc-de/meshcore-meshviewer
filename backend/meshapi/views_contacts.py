from typing import List, Dict, Any

from django.db.models import OuterRef, Subquery
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import Contact, ContactTelemetry


class ContactsLatestView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # Subquery to fetch latest telemetry per contact
        latest_qs = (
            ContactTelemetry.objects
            .filter(contact=OuterRef('pk'))
            .order_by('-fetched_at')
        )

        contacts = (
            Contact.objects
            .all()
            .annotate(
                _adv_name=Subquery(latest_qs.values('adv_name')[:1]),
                _last_advert=Subquery(latest_qs.values('last_advert')[:1]),
                _adv_lat=Subquery(latest_qs.values('adv_lat')[:1]),
                _adv_lon=Subquery(latest_qs.values('adv_lon')[:1]),
                _rssi=Subquery(latest_qs.values('rssi')[:1]),
                _snr=Subquery(latest_qs.values('snr')[:1]),
                _battery_mv=Subquery(latest_qs.values('battery_mv')[:1]),
                _battery_percent=Subquery(latest_qs.values('battery_percent')[:1]),
                _type=Subquery(latest_qs.values('type')[:1]),
                _flags=Subquery(latest_qs.values('flags')[:1]),
                _out_path_len=Subquery(latest_qs.values('out_path_len')[:1]),
                _out_path=Subquery(latest_qs.values('out_path')[:1]),
                _lastmod=Subquery(latest_qs.values('lastmod')[:1]),
                _fetched_at=Subquery(latest_qs.values('fetched_at')[:1]),
            )
            .order_by('-last_seen')
        )

        items: List[Dict[str, Any]] = []
        for c in contacts:
            items.append({
                'name': c.name or c._adv_name or '',
                'public_key': c.public_key,
                'last_seen': c.last_seen,
                'first_seen': c.first_seen,
                'adv_name': c._adv_name,
                'last_advert': c._last_advert,
                'adv_lat': c._adv_lat,
                'adv_lon': c._adv_lon,
                'rssi': c._rssi,
                'snr': c._snr,
                'battery_mv': c._battery_mv,
                'battery_percent': c._battery_percent,
                'type': c._type,
                'flags': c._flags,
                'out_path_len': c._out_path_len,
                'out_path': c._out_path,
                'lastmod': c._lastmod,
                'telemetry_fetched_at': c._fetched_at,
            })

        return Response({
            'fetched_at': timezone.now(),
            'items': items,
        })
