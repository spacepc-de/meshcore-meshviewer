#!/usr/bin/env sh
set -e

# Apply migrations
python manage.py migrate --noinput

# Collect static files for admin and app
python manage.py collectstatic --noinput

# Start gunicorn
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:${BACKEND_PORT:-8000} \
  --workers 3 \
  --timeout 120
