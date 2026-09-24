# Automatic Deployment

Push to `main`, and within a few minutes the Pi is running it: the API, the web
panel, the systemd units and the game server, each updated only when a commit
actually changed it.

## What runs where

The Pi runs two kinds of thing, and they update differently:

| Part | Runs from | Kept current by |
| --- | --- | --- |
| Game server | A Docker image | `minecraft-update.timer` (hourly) and the deploy agent |
| API (`api/`), web panel (`web/`), systemd units, nginx config | The git checkout in `~/minecraft-server` | The deploy agent, `minecraft-deploy.timer` (every 5 minutes) |

Before the deploy agent, only the image had any automation, so every change to
the API or the panel meant logging in to pull and rebuild by hand.

## How a deploy works

The Pi pulls; nothing pushes into the house. There is no inbound port to open
and no CI runner on the machine that holds the world and its backups.

```text
push to main -> CI runs -> the Pi notices the new commit
             -> CI passed? -> fast-forward -> apply what changed
                                           -> healthy? keep it : roll back
```

Every five minutes, `scripts/deploy-agent.sh run`:

1. Fetches `main`. If there is no new commit, it stops there.
2. Asks GitHub whether that commit's `main.yml` run passed. Still running means
   wait for the next tick. Failed means it is never deployed.
3. Fast-forwards the checkout and works out what changed across **every**
   commit since the last deploy, not just the newest one.
4. Applies only what changed:

   | Changed | What happens |
   | --- | --- |
   | `web/` | The panel is built (or downloaded from CI) into a staging directory, then swapped in once the API is healthy. nginx serves it from disk, so no reload is needed |
   | `api/requirements.txt` | The API's virtualenv is updated |
   | `api/` or `systemd/` | The API is restarted and must answer `/api/health` within 60 seconds |
   | `systemd/` | Unit files are installed and systemd is reloaded |
   | `config/nginx-minecraft.conf` | `nginx -t`, then a reload if the config is valid |
   | `Dockerfile`, compose files, `server.properties`, `scripts/start.sh` | The image is pulled or rebuilt, and the game server restarts **only when nobody is online** |
   | Anything else (docs, tests) | Nothing restarts |

5. Writes the result to the audit log (`deploy.success`, `deploy.rollback`,
   `deploy.server_restart`), and sends a push notification if one is configured.

### What it will not do

- **Restart the game while someone is playing.** It asks the server how many
  players are online (the same status ping the multiplayer screen uses). If
  anyone is on, or the server does not answer, the restart waits and is tried
  again on every run until the server is empty.
- **Start a server that was stopped.** A server stopped for bedtime or
  maintenance stays stopped, and starts on the new version whenever it is next
  started.
- **Deploy over local edits.** If a tracked file was edited on the Pi, it logs
  that and does nothing until the edit is committed or discarded.
- **Deploy anything but `main`.** If the checkout is on another branch because
  you are testing something, it leaves it alone.
- **Retry a commit that failed.** If the web build fails, dependencies fail to
  install, or the API fails its health check, the checkout goes back to the
  previous commit, and whatever was restarted is restarted on the old code.
  That commit is skipped from then on. The next commit is tried as normal.

## Setting it up

Everything here runs on the Pi, as the `pi` user, in `~/minecraft-server`.

### 1. Check the prerequisites

This is the last pull you do by hand: the agent is part of the code it
deploys, so the Pi needs it once before it can take over.

```bash
cd ~/minecraft-server
git pull                    # brings in scripts/deploy-agent.sh and its units
git status                  # on branch main, nothing modified
sudo -n true && echo ok     # passwordless sudo, which Raspberry Pi OS gives `pi` by default
ls api/venv/bin/pip         # the API's virtualenv; if missing, run scripts/setup-api-venv.sh
```

The agent uses `sudo -n` to restart the API, install units and reload nginx.
`-n` means it fails instead of waiting for a password, so a missing sudo rule
shows up as a failed step in the log rather than a hung deploy. To allow only
what it needs instead of full sudo, see [Narrower sudo](#narrower-sudo).

If `git status` shows local edits, commit them or move them out first. If you
had copied `docker-compose.registry.yml` over `docker-compose.yml`, undo that
with `git checkout docker-compose.yml` and follow step 4 instead.

### 2. Configure it (optional)

It works with no configuration. To change anything, copy the example:

```bash
cp config/deploy.conf.example config/deploy.conf
nano config/deploy.conf
```

| Setting | Default | Why you would change it |
| --- | --- | --- |
| `DEPLOY_GITHUB_TOKEN` | empty | Needed if the repository is private. On a public one it also lets the Pi download CI's web build rather than running `npm` itself. Use a fine-grained token for this one repository with **Actions: read** and **Contents: read**, nothing else |
| `DEPLOY_NTFY_URL` | empty | Push notifications for deploys and rollbacks, e.g. `https://ntfy.sh/<a-long-random-topic>` |
| `DEPLOY_REQUIRE_CI` | `true` | Leave it on. Off means a broken commit reaches the Pi in five minutes |
| `DEPLOY_BRANCH` | `main` | To follow a different branch |

`config/deploy.conf` is gitignored, so the token never leaves the Pi.

The web panel is always built on the Pi, even with a token, when `web/.env`
(or `.env.production`) exists. Vite bakes those `VITE_*` settings, such as the
API URL, into the bundle at build time, and CI does not have them.

### 3. Turn it on

```bash
sudo cp systemd/minecraft-deploy.service systemd/minecraft-deploy.timer /etc/systemd/system/
sudo systemctl daemon-reload

# See what the first run would do, without doing it
scripts/deploy-agent.sh check

sudo systemctl enable --now minecraft-deploy.timer
```

### 4. Keep the game server image current

The hourly `minecraft-update.timer` brings the game server onto a new image,
with the same rule as above: never while someone is playing.

The image can come from either place:

- **Built on the Pi** (the default `docker-compose.yml`). When a deploy changes
  the `Dockerfile` or anything the image copies in, the agent rebuilds it.
- **Pulled from the registry.** CI publishes
  `ghcr.io/and3rn3t/minecraft-server:latest` on every push to `main`, which
  saves the Pi from building anything. Select it with one line in `.env`
  (gitignored), rather than by copying files over tracked ones, so the
  checkout stays clean for the agent:

  ```bash
  echo "COMPOSE_FILE=docker-compose.registry.yml" >> .env
  ```

  If the package is private, log the Pi in once with a classic token that has
  only `read:packages`:

  ```bash
  echo "YOUR_TOKEN" | docker login ghcr.io -u and3rn3t --password-stdin
  ```

Then enable the hourly check:

```bash
sudo cp systemd/minecraft-update.service systemd/minecraft-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now minecraft-update.timer
```

## Day to day

```bash
scripts/deploy-agent.sh status                  # last deploy, a failed commit, a waiting restart
scripts/deploy-agent.sh check                   # what the next run would do
journalctl -u minecraft-deploy.service -n 50    # what recent runs did
sudo systemctl start minecraft-deploy.service   # deploy now instead of waiting
sudo systemctl stop minecraft-deploy.timer      # pause deploys, e.g. while testing on the Pi
```

Deploys also appear in the admin panel's audit log as the user `deploy-agent`.

## Troubleshooting

**"Tracked files have local edits; not deploying."** Something in the checkout
was edited on the Pi. `git status` shows what. Commit it to a branch and push,
or `git checkout -- <file>` to discard it. Settings belong in gitignored files
(`config/*.conf`, `.env`, `web/.env`), and edits to a systemd unit belong in a
drop-in (`sudo systemctl edit minecraft-api.service`), which survives the
units being reinstalled.

**"Could not read CI status."** GitHub did not answer, or the repository is
private and `DEPLOY_GITHUB_TOKEN` is not set. It tries again on the next run.

**"failed to deploy before; waiting for a newer commit."** The last deploy
rolled back. `journalctl -u minecraft-deploy.service` shows why, and
`logs/api-server.log` shows why the API would not start. Push a fix; the new
commit is tried automatically.

**"Game server update waiting: 2 player(s) online."** Working as intended. It
restarts on the first run after everyone leaves.

**A web build on the Pi fails with out-of-memory.** Set `DEPLOY_GITHUB_TOKEN`
and remove `web/.env` if it only holds defaults, so the Pi downloads CI's build
instead.

**Image pull fails with 403.** The Pi's `docker login` expired or was never
done; repeat the login in step 4.

## Narrower sudo

Instead of full passwordless sudo for `pi`, allow just the commands the agent
runs. Create it with `sudo visudo -f /etc/sudoers.d/minecraft-deploy`:

```text
pi ALL=(root) NOPASSWD: /usr/bin/systemctl restart minecraft-api.service, \
    /usr/bin/systemctl daemon-reload, \
    /usr/bin/systemctl reload nginx, \
    /usr/sbin/nginx -t, \
    /usr/bin/cp /home/pi/minecraft-server/systemd/* /etc/systemd/system/
```

Be clear about what this buys. The `cp` rule is, in effect, root for the `pi`
account: a unit file can run anything as root, and the wildcard does not pin
which files are copied. So the narrower list guards against a script doing
something by accident, not against someone who already controls `pi`. What
keeps unreviewed code off the Pi is that the checkout only ever fast-forwards
to commits on `main` that passed CI.

## Related

- [UPDATE_CODEBASE.md](UPDATE_CODEBASE.md) — updating by hand
- [UPDATE_DOCKER_IMAGE.md](UPDATE_DOCKER_IMAGE.md) — the image build itself
- [CI_CD.md](CI_CD.md) — what CI runs before a commit counts as green
