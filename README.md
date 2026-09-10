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

| Method | Path          | Purpose                                  |
| ------ | ------------- | ---------------------------------------- |
| GET    | `/api/health` | Liveness                                 |
| GET    | `/api/scans`  | All retained scans, oldest first         |
| POST   | `/api/scans`  | Record a scan (`serialNumber`, `records`) |
| DELETE | `/api/scans`  | Clear all scans                          |

Storage is a 500-entry in-memory ring; restarting the server discards everything. There is
no authentication, so anyone on the network can read and post scans.

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
