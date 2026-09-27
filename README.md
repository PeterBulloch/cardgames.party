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

Cards ships as a single Docker image that serves the web app and API over **plain HTTP**. Put it
behind anything that terminates HTTPS — a hosting platform, Caddy, nginx, Traefik — and it just
works. HTTPS matters: phones only allow NFC scanning on secure pages.

With Docker Compose (publishes host port `80` to container port `8000` on all interfaces):

```sh
docker compose up -d --build
```

Or with plain Docker:

```sh
docker build -t cards .
docker run -d --name cards --restart unless-stopped -p 80:8000 cards
```

Check it is up with `curl http://127.0.0.1/api/health`, which also reports the running
version. The image has a built-in health check.

To test from another device on the same LAN, start the Compose service and open
`http://<server-lan-ip>/` from that device. For example, if the server is
`192.168.0.100`, use `http://192.168.0.100/`. Allow inbound TCP port `80` through the server's
firewall on its private network profile. This plain-HTTP test is suitable for checking network
reachability; phones require HTTPS for NFC.

### Reverse proxy

The proxy must pass WebSocket upgrades for `/api/ws`. For a proxy on another LAN host, forward to
the Cards server's LAN address on port `80`. Caddy does this automatically:

```caddyfile
cards.example.com {
  reverse_proxy 192.168.0.100:80
}
```

With nginx, forward `Upgrade` and `Connection` headers and raise `proxy_read_timeout` so idle
tables are not disconnected.

### Configuration

| Variable              | Default     | Purpose                                                              |
| --------------------- | ----------- | -------------------------------------------------------------------- |
| `PORT`                | `8000`      | Port the server listens on inside the container                     |
| `CARDS_BIND_IP`       | `0.0.0.0`   | Host address Compose publishes on                                   |
| `CARDS_PORT`          | `80`        | Host port Compose publishes                                          |
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
