# syntax=docker/dockerfile:1

FROM node:22-alpine AS web
WORKDIR /build
COPY VERSION /VERSION
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv

# curl is only used by CARDS_TLS=local-ip to fetch the LAN certificate.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION ./VERSION
COPY server/app ./app
COPY --from=web /build/dist ./web/dist
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Ownership is inherited by a fresh named volume mounted here.
RUN useradd --create-home --uid 10001 cards \
    && mkdir -p /certs \
    && chown cards:cards /certs
USER cards

ENV CARDS_DIST_DIR=/srv/web/dist \
    CARDS_CERT_DIR=/certs \
    CARDS_TLS="" \
    PORT=8000

EXPOSE 8000
# Self-check over loopback; the local-ip certificate does not name 127.0.0.1, hence no verification.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, ssl, urllib.request; scheme = 'https' if os.environ.get('CARDS_TLS') else 'http'; urllib.request.urlopen(scheme + '://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health', context=ssl._create_unverified_context(), timeout=4)" || exit 1
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
