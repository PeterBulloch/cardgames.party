#!/bin/sh
# Production (default): plain HTTP; TLS is terminated by the platform or reverse proxy in front.
# CARDS_TLS=local-ip: serve HTTPS with the public local-ip.sh certificate for LAN use.
set -eu

PORT="${PORT:-8000}"

case "${CARDS_TLS:-}" in
    "")
        exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
        ;;
    local-ip)
        ;;
    *)
        echo "ERROR: unknown CARDS_TLS='$CARDS_TLS' (expected empty or 'local-ip')." >&2
        exit 1
        ;;
esac

# Refreshes the public local-ip.sh certificate on every start, so it can never expire
# in place. Falls back to the cached copy in the volume when offline.
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
    --port "$PORT" \
    --ssl-certfile "$CERT" \
    --ssl-keyfile "$KEY"
