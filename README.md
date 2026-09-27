# Cards

A self-hosted table for playing real card games with physical cards. The server hosts the
game state for each lobby and pushes it to every connected phone or screen, so the table
can track hands, turns, chips and pots while you deal real cards, entered by NFC scan or by
tapping them in.

Texas Hold'em is the first supported game; the server and client are organised so more games
can be added alongside it.

## Features

- **Lobbies** — create one with a name, optional password, game and seat count, then share the
  name. Players join by name as a **player**, **dealer** or **observer**.
- **Per-viewer state** — the server decides what each client may see. Players see their own
  hand and public cards; dealers and observers see everything. Observers can switch to a
  public-only view for a shared TV.
- **Server-authoritative rules** — clients only render state. The server enforces turn order,
  deal order, burns, legal bets and stage progression, so nobody can act out of turn.
- **Texas Hold'em** — rotating button, blinds (with optional automatic doubling), no-limit
  betting, all-ins with side pots, showdown hand evaluation and split pots.
- **Chips** — any player or dealer can adjust stacks and pots at any time, to set up a table
  or correct mistakes. Undo steps back through any number of recent actions.
- **Card entry** — scan NFC-tagged cards (Chrome on Android) or pick them from a visual
  suit and rank picker. The server works out where each card goes next.
- **Tag tools** — `/scanner` reads and writes card NFC tags.

## Running in production

Cards ships as a single Docker image that serves the web app and API over **plain HTTP on
port 8000**. Put it behind anything that terminates HTTPS — a hosting platform, Caddy, nginx,
Traefik — and it just works. HTTPS matters: phones only allow NFC scanning on secure pages.

With Docker Compose (binds to `127.0.0.1:8000` for a reverse proxy on the same host):

```sh
docker compose up -d --build
```

Or with plain Docker:

```sh
docker build -t cards .
docker run -d --name cards --restart unless-stopped -p 8000:8000 cards
```

Check it is up with `curl http://127.0.0.1:8000/api/health`, which also reports the running
version. The image has a built-in health check.

### Reverse proxy

The proxy must pass WebSocket upgrades for `/api/ws`. Caddy does this automatically:

```caddyfile
cards.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

With nginx, forward `Upgrade` and `Connection` headers and raise `proxy_read_timeout` so idle
tables are not disconnected.

### Configuration

| Variable              | Default     | Purpose                                                              |
| --------------------- | ----------- | -------------------------------------------------------------------- |
| `PORT`                | `8000`      | Port the server listens on inside the container                     |
| `CARDS_BIND_IP`       | `127.0.0.1` | Host address Compose publishes on; use `0.0.0.0` only behind a firewall or proxy |
| `CARDS_PORT`          | `8000`      | Host port Compose publishes                                          |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Proxies trusted for `X-Forwarded-*` headers (Uvicorn setting)        |
| `CARDS_TLS`           | *(empty)*   | Set to `local-ip` for LAN HTTPS; see [CONTRIBUTING.md](CONTRIBUTING.md) |

### Operational notes

- **Run one process.** All lobbies live in memory, so run a single container with a single
  worker. Restarting discards every lobby.
- **Lobbies expire** after 60 minutes with nobody connected or 60 minutes without activity.
- **Security.** Lobby passwords are scrypt-hashed and each member gets an unguessable session
  token. The `/scanner` scan log (`/api/scans`) has no authentication: anyone who can reach
  the server can read, add or clear scans.

## Local development and LAN play

Running on your own network uses [local-ip.sh](https://local-ip.sh) certificates so phones get
HTTPS without installing anything. See [CONTRIBUTING.md](CONTRIBUTING.md) for LAN hosting, the
hot-reload dev setup, tests, the WebSocket protocol and how to add a game.

## Versioning

Cards follows [Semantic Versioning](https://semver.org). The current version is in
[`VERSION`](VERSION), shown on the home page and returned by `/api/health`. Changes are listed
in [CHANGELOG.md](CHANGELOG.md).
