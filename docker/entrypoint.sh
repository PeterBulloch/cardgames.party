#!/bin/sh
# Refreshes the public local-ip.sh certificate on every start, so it can never expire
# in place. Falls back to the cached copy in the volume when offline.
set -eu

CERT_DIR="${CARDS_CERT_DIR:-/certs}"
CERT="$CERT_DIR/server.pem"
KEY="$CERT_DIR/server.key"

if curl -fsS --max-time 20 -o "$CERT.tmp" https://local-ip.sh/server.pem \
    && curl -fsS --max-time 20 -o "$KEY.tmp" https://local-ip.sh/server.key; then
    mv "$CERT.tmp" "$CERT"
    mv "$KEY.tmp" "$KEY"
    chmod 600 "$KEY"
    echo "Fetched a fresh local-ip.sh certificate."
else
    rm -f "$CERT.tmp" "$KEY.tmp"
    if [ -f "$CERT" ] && [ -f "$KEY" ]; then
        echo "WARNING: could not reach local-ip.sh; using the cached certificate." >&2
    else
        echo "ERROR: could not reach local-ip.sh and no cached certificate exists." >&2
        exit 1
    fi
fi

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8443}" \
    --ssl-certfile "$CERT" \
    --ssl-keyfile "$KEY"
