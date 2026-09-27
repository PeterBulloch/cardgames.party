# Contributing

## Project layout

```text
server/app/            FastAPI app (Python 3.12)
  main.py              HTTP routes, WebSocket route, static SPA hosting
  controller.py        WebSocket session handling and broadcasting
  models.py            Request and lobby-level message schemas
  rooms/               Lobbies and the lobby registry
  games/               Generic game base, players, cards, undo, game registry
    poker/             Poker-specific code: hand evaluator, pots, Texas Hold'em
server/tests/          pytest suite
web/src/               React + Vite client
  games/               Client game registry
    texasHoldEm/       Texas Hold'em table, betting and blinds UI
docker/entrypoint.sh   Container start-up (production HTTP or local-ip HTTPS)
scripts/               PowerShell helpers for LAN hosting
```

Keep generic code generic and game-specific code inside that game's package (`games/poker/`
on the server, `web/src/games/<game>/` on the client).

## LAN hosting with local-ip.sh

Web NFC (`NDEFReader`) is only exposed in a secure context, so a plain
`http://192.168.x.x` page has no NFC at all. For LAN use this project relies on
[local-ip.sh](https://local-ip.sh): a public DNS service where `192-168-1-10.local-ip.sh`
resolves to `192.168.1.10`, published together with a genuine Let's Encrypt wildcard
certificate **and its private key**. Android already trusts Let's Encrypt, so there is nothing
to install on the phone, and because DNS points at a private address the traffic never leaves
your network.

> The private key is public by design. The connection is encrypted but not authenticated —
> fine on your own LAN, unsuitable for production. Production deployments use a real
> certificate at the proxy instead (see the README).

Docker is the only prerequisite. Run this on the host machine, not the phone:

```powershell
./scripts/start.ps1
```

The script finds the host's private LAN address, prints the URL to open on phones, then
builds and starts the stack with `docker-compose.local.yml` layered on top of the production
compose file. Add `-Detach` to run it in the background, or `-Port 8443` to avoid binding 443.
Stop it with `docker compose down`.

- The URL has no port number on purpose: Chrome only defaults to `https://` for a typed
  address when no port is present.
- The port is published on the private address only, never `0.0.0.0`. If the host has no
  private (RFC1918) address, the script refuses to start.
- The container re-downloads the certificate on every start, so it can never quietly expire.
  If the download fails it falls back to the cached copy in the `certs` volume.
- Give the host a static or DHCP-reserved IP, because the hostname is derived from it.
- **Use Chrome on Android** for scanning. Firefox for Android does not implement Web NFC.

## Hot-reload development

Run the two halves directly. Vite terminates TLS with the local-ip.sh certificate and proxies
`/api` (including the WebSocket) to the backend.

```powershell
./scripts/fetch-cert.ps1                                  # once, into certs/
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r server/requirements-dev.txt
cd server; uvicorn app.main:app --port 8000 --reload      # terminal 1
cd web; npm install; npm run dev                          # terminal 2
```

Open `https://<dashed-ip>.local-ip.sh:5173`. Without `certs/`, Vite falls back to plain HTTP on
`http://localhost:5173`, which works for everything except NFC.

## Checks

```powershell
cd server; python -m pytest       # server tests, including version/changelog consistency
cd web; npm run build             # type-check and production build
```

## API and WebSocket protocol

| Method | Path                | Purpose                                                           |
| ------ | ------------------- | ----------------------------------------------------------------- |
| GET    | `/api/health`       | Liveness and version                                              |
| POST   | `/api/lobbies`      | Create a lobby and join it; returns `{lobby_id, member_id, token}` |
| POST   | `/api/lobbies/join` | Join a lobby by name and password; same response                  |
| WS     | `/api/ws`           | Live game state for a lobby member                                |
| GET    | `/api/scans`        | Scanner page: retained scans, oldest first                        |
| POST   | `/api/scans`        | Scanner page: record a scan (`serialNumber`, `records`)           |
| DELETE | `/api/scans`        | Scanner page: clear all scans                                     |

The WebSocket's first frame must be `{"type": "hello", "token": "..."}`. Actions are then sent as:

```json
{"lobby": "<lobby_id>", "player": "<member_id>", "seq": 1, "sent_at": "<iso time>",
 "action": {"type": "deal_card", "card": "CARD_SPADE_ACE"}}
```

The server replies with `ack` or `error` for the sender's `seq`, then pushes
`{"type": "state", "version", "updated_at", "state"}` to every client, filtered per viewer.
`version` increases with every change so clients discard older snapshots; a `seq` that does
not increase on a connection is ignored as a replay.

- **Lobby actions:** `set_view` (observers), `leave`.
- **Any game:** `undo` steps back one action; repeatable, cleared when someone joins or leaves.
- **Texas Hold'em:**
  - `start_hand`
  - `deal_card` — the server decides whether it goes to the next seat, the burn pile or the board
  - `fold` / `check` / `call`, and `bet` / `raise` with `amount` (the player's total for the
    street), each with the `member_id` of the player on turn
  - `award_pots`
  - `set_blinds` between hands, with optional `auto_double` every `double_every` hands
  - `set_chips` / `set_pot`, allowed at any time

Any player or dealer may submit a move, but only for whoever's turn it is, and only moves legal
at that moment. The button rotates each hand and sets the blinds; a member with the dealer role
handles the cards without taking a seat.

## Adding a game

1. Server: add a package under `server/app/games/<game>/` with an `actions.py` (a Pydantic
   `TypeAdapter` of the game's actions) and a `Game` subclass implementing `apply` and
   `view_for`. Register it in `games/registry.py`.
2. Client: add `web/src/games/<game>/` with its view/action types and a table component, and
   register it in `web/src/games/index.ts`.

## Releasing

1. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new `## [x.y.z] - YYYY-MM-DD`
   heading and update the compare links at the bottom.
2. Bump `VERSION` and `web/package.json` (`npm version x.y.z --no-git-tag-version` in `web/`).
   The server test suite fails if these or the changelog disagree.
3. Commit, then tag: `git tag vx.y.z; git push --tags`.

## Troubleshooting LAN hosting

**The start script says no private address was found.** The PC is not behind NAT. On Korean
ISP routers the first port is often a bridged IPTV passthrough (labelled `IPTV` / `IP TU`)
that skips the router entirely and hands out a public ISP address. Move the cable to a
normal numbered LAN port.

**The hostname will not resolve.** Some routers enable DNS rebinding protection, which
discards public DNS answers pointing at private IPs. They all support an exception list —
look for "DNS rebind protection" and allow `local-ip.sh`. Check what actually resolves:

```powershell
Resolve-DnsName 192-168-0-11.local-ip.sh    # should return the PC's LAN IP
```

**The phone cannot reach it but the host can.** Check the router does not have AP isolation
(client isolation) enabled, and allow inbound TCP 443 through Windows Firewall on the
private network profile.

**"The proxy server is refusing connections", or the request never appears in
`docker compose logs`.** The browser is routing through a proxy. Firefox keeps its own proxy
settings independent of Windows: Settings > search "proxy" > Network Settings, then either
select "No proxy" or add `local-ip.sh` to "No proxy for". Also check for VPN or proxy
extensions.

**ERR_EMPTY_RESPONSE.** The URL was opened as `http://`. The LAN server is TLS-only, so the
scheme must be `https://`. This is why the default URL carries no port number.
