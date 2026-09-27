# Card Scanner

LAN-only NFC tag reader. A FastAPI server serves a React SPA over HTTPS; Chrome on Android
uses Web NFC to read tag serial numbers and POSTs them back, where they are kept in memory
and displayed.

## Why HTTPS is mandatory

`NDEFReader` is only exposed in a secure context, so a plain `http://192.168.x.x` page will
not have the API at all. This project uses [local-ip.sh](https://local-ip.sh): a public DNS
service where `192-168-1-10.local-ip.sh` resolves to `192.168.1.10`, published together with
a genuine Let's Encrypt wildcard certificate **and its private key**. Android already trusts
Let's Encrypt, so there is nothing to install on the phone, and because DNS points at a
private address the traffic never leaves your network.

> The private key is public by design. The connection is encrypted but not authenticated —
> fine for tag UIDs on your own LAN, unsuitable for anything sensitive.

## Run

Everything — the frontend build, the Python environment, and the certificate — is handled
inside the container. Docker is the only prerequisite. Run this on the host machine, not
on the phone; the phone only ever opens a URL.

```powershell
./scripts/start.ps1
```

The script prints the URL to open on the phone, then builds and starts the stack. Add
`-Detach` to run it in the background, or `-Port 8443` to avoid binding 443.

The URL has no port number on purpose: Chrome only defaults to `https://` for a typed
address when no port is present. Any number of phones can open it at once.

**Use Chrome on Android.** Firefox for Android does not implement Web NFC, so scanning will
not work there even though the page loads.

Give the host machine a static or DHCP-reserved IP, because the hostname is derived from it.

The port is published on that private address only, never `0.0.0.0`. If the host has no
private (RFC1918) address, the script refuses to start rather than exposing an
unauthenticated service to the internet.

The container re-downloads the certificate on every start, so it can never quietly expire.
If the download fails it falls back to the cached copy in the `certs` volume.

Stop it with `docker compose down`.

## Development

For hot reloading, run the two halves directly instead of in Docker. Vite terminates TLS and
proxies `/api` to the backend.

```powershell
./scripts/fetch-cert.ps1                                 # once, into certs/
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r server/requirements.txt
cd server; uvicorn app.main:app --port 8000 --reload      # terminal 1
cd web; npm install; npm run dev                          # terminal 2
```

Open `https://<dashed-ip>.local-ip.sh:5173`.

## API

| Method | Path                | Purpose                                                   |
| ------ | ------------------- | --------------------------------------------------------- |
| GET    | `/api/health`       | Liveness                                                  |
| POST   | `/api/lobbies`      | Create a lobby and join it; returns `{lobby_id, member_id, token}` |
| POST   | `/api/lobbies/join` | Join a lobby by name and password; same response          |
| WS     | `/api/ws`           | Live game state for a lobby member                        |
| GET    | `/api/scans`        | All retained scans, oldest first                          |
| POST   | `/api/scans`        | Record a scan (`serialNumber`, `records`)                 |
| DELETE | `/api/scans`        | Clear all scans                                           |

The homepage is the lobby; the original scanner and tag writer live at `/scanner`.

### Lobbies

Roles: `player` (sees own hand and public cards, can act), `dealer` (sees everything, can
act), `observer` (sees everything, cannot act, can switch to a public-only view). Lobbies are
deleted after 60 minutes with no connected clients or 60 minutes with no activity.

The WebSocket's first frame must be `{"type": "hello", "token": "..."}`. Actions are then sent as:

```json
{"lobby": "<lobby_id>", "player": "<member_id>", "seq": 1, "sent_at": "<iso time>",
 "action": {"type": "deal_card", "card": "CARD_SPADE_ACE"}}
```

Lobby actions: `set_view` (observers), `leave`. Any game: `undo` (steps back one action; repeatable,
cleared when someone joins or leaves). Texas Hold'em: `start_hand`, `deal_card` (the server
decides whether it goes to the next seat, the burn pile or the board), and `fold` / `check` /
`call` / `bet` / `raise` with the `member_id` of the player on turn. Any player or dealer may
submit a move, but only for whoever's turn it is, and only moves legal at that moment. The
button rotates each hand and sets the blinds; a member with the dealer role handles the cards
without taking a seat. The server replies with `ack` or
`error` for the sender's `seq`, then pushes `{"type": "state", "version", "updated_at", "state"}`
to every client, filtered per viewer. `version` increases with every change so clients discard
older snapshots; a `seq` that does not increase on a connection is ignored as a replay.

All state is in memory, so restarting the server discards lobbies and scans. Lobby passwords
are scrypt-hashed; the scan API has no authentication.

Run the server tests with `pip install -r server/requirements-dev.txt; cd server; python -m pytest`.

## Troubleshooting

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

**ERR_EMPTY_RESPONSE.** The URL was opened as `http://`. The server is TLS-only, so the
scheme must be `https://`. This is why the default URL carries no port number.
