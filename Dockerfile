# syntax=docker/dockerfile:1

FROM node:22-alpine AS web
WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

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
    PORT=8443

EXPOSE 8443
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
