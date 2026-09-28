# Game Access Through playit.gg

How players outside the house reach the server, and why it isn't a port
forward.

## Why playit.gg

The home internet connection is behind **CGNAT** (carrier-grade NAT): the
router's WAN address is a private address shared with other customers, not
the public IP that sites like ipify report. Nothing on the internet can open
a connection to the house, so a router port forward on 25565 cannot work, and
there is no public IPv6 to fall back on.

playit.gg works around that. An agent on the Pi makes an outbound connection
to playit's servers, and players connect to playit, which relays each
connection back down the agent's link to the server on `127.0.0.1:25565`.

Cloudflare still owns the name. Players type the family hostname
(`mine.andernet.dev`); a Cloudflare **SRV record** on it tells their client
the tunnel's real host and port.

Cloudflare Tunnel can't replace playit here: it carries the admin panel
(HTTP), but for game traffic every player would need `cloudflared` or WARP
running on their own PC. Cloudflare's product for game traffic, Spectrum, is
paid and expects an origin it can reach.

## How it fits together

```text
player types mine.andernet.dev
  -> SRV _minecraft._tcp.mine.andernet.dev (Cloudflare)
       = della-bd.tun.ply.gg:33903
  -> playit.gg edge
  -> playit agent on the Pi (outbound link, minecraft-playit.service)
  -> 127.0.0.1:25565 (the minecraft-server container)
```

| Piece | Where | Managed by |
| --- | --- | --- |
| Agent binary and claim secret | `~/playit/` on the Pi (outside the repo) | Downloaded by hand, once |
| Agent service | `systemd/minecraft-playit.service` | The repo |
| Tunnel (type Minecraft Java, local `127.0.0.1:25565`) | playit.gg dashboard | By hand |
| SRV record `_minecraft._tcp.mine.andernet.dev` | Cloudflare DNS | `scripts/playit-srv-sync.sh`, every 15 min |

The A record for `mine.andernet.dev` and the DDNS updater that maintained it
([DYNAMIC_DNS.md](DYNAMIC_DNS.md)) point at the CGNAT address, where nothing
answers. Game clients follow the SRV record first, so the A record is unused.

## The port can change

playit can move a tunnel to a new port without warning. It moved this one from
33856 to 33903, and `mine.andernet.dev` stopped working without any error on
the Pi: the agent was connected and healthy, and the dashboard showed no port
at all.

playit publishes the tunnel's current host and port as an SRV record on its
own hostname (`_minecraft._tcp.della-bd.tun.ply.gg`).
`scripts/playit-srv-sync.sh` reads that record over DNS-over-HTTPS and copies
the port and host into the Cloudflare record when they differ:

```bash
scripts/playit-srv-sync.sh check   # report; exits 1 when they differ
scripts/playit-srv-sync.sh sync    # fix the Cloudflare record
```

It only ever updates the one existing record. It refuses to write anything
when playit's answer is missing, names a different host, or has an invalid
port, or when the Cloudflare record isn't exactly one match.

## Setup

### 1. The agent

Download the `aarch64` agent from
[playit-cloud/playit-agent releases](https://github.com/playit-cloud/playit-agent/releases)
into `~/playit/`, then claim it to the playit.gg account:

```bash
cd ~/playit
./playit-cli setup      # prints a claim link; approve it in the browser
```

Then run it as a service:

```bash
sudo cp ~/minecraft-server/systemd/minecraft-playit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft-playit.service
```

The agent logs to `~/playit/playit.log`. The "failed to send initial ping ...
Network unreachable" error at startup is its IPv6 probe and is harmless; the
line that matters is `playit connected; tunnels loaded ... tunnel_count=1`.

### 2. The tunnel

In the playit.gg dashboard, create a **Minecraft Java** tunnel for the agent
with local address `127.0.0.1`, port `25565`. Note its public address
(`della-bd.tun.ply.gg`).

### 3. The SRV record

In Cloudflare DNS for `andernet.dev`, create an SRV record: name
`_minecraft._tcp.mine`, priority `0`, weight `5`, target the tunnel's public
address, and the port from `dig +short SRV _minecraft._tcp.<tunnel address>`.
After that, the sync keeps it right.

### 4. The sync

```bash
cp config/playit.conf.example config/playit.conf
chmod 600 config/playit.conf      # it holds a Cloudflare token
# set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID; config/ddns.conf's token has the right scope
scripts/playit-srv-sync.sh check

sudo cp systemd/minecraft-playit-sync.service systemd/minecraft-playit-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft-playit-sync.timer
```

## Troubleshooting

**Players can't connect.** Work outwards from the server:

1. The agent: `systemctl status minecraft-playit` and the end of
   `~/playit/playit.log`. A connection attempt that reaches the Pi logs
   `New TCP Client`; if none appears, the problem is before the Pi.
2. The records: `scripts/playit-srv-sync.sh check`, or compare
   `dig +short SRV _minecraft._tcp.mine.andernet.dev` with
   `dig +short SRV _minecraft._tcp.della-bd.tun.ply.gg` by hand.
3. The tunnel: in the dashboard, check it is enabled and assigned to the
   `minecraft-server` agent.

Connecting to the tunnel's hostname directly (`della-bd.tun.ply.gg`, with no
port) also works, which separates a DNS problem from a tunnel problem. Players
should enter hostnames without a port, so their client follows the SRV
record.

**The agent is running but stuck.** It once sat in a reconnect loop
(`control session expired; reconnecting reason=Forced`) for three days.
`sudo systemctl restart minecraft-playit` cleared it.

**"account is over the agent limit".** The free plan allows a limited number
of agents. Delete unused ones in the dashboard, then restart the service.
