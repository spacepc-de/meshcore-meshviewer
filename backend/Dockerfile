FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install meshcore-cli so the backend can talk to the device directly
# (the contacts/info endpoints auto-detect it when MESHCORE_TARGET is set)
RUN pip install --no-cache-dir meshcore-cli

COPY . /app

EXPOSE 8000

CMD ["/bin/sh", "-lc", "./entrypoint.sh"]
