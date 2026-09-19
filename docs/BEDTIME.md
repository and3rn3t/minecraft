# Bedtime Mode

A scheduled, warned, enforceable end to the evening.

A shutdown that arrives without warning starts an argument. Bedtime gives a
countdown instead: a bossbar that empties, titles at the agreed marks, and a
goodnight message. The end of the evening becomes something the server
announced rather than something a parent did.

## What players see

```
[30 minutes until bedtime]     title, with a bossbar appearing
[10 minutes until bedtime]
[5 minutes until bedtime]
[1 minute until bedtime]
Goodnight. The server is closing.
```

Then, depending on the configured action, the server saves and stops, or
everyone is removed and the server stays up.

## The closed window

Bedtime is a window, not a moment. Between bedtime and the wake time, anyone who
joins is sent straight back out with a message saying when the server opens
again.

That is the part that makes it hold. Stopping the server is not enough on its
own: a restart policy, an update timer, or somebody pressing start on the
dashboard all reopen the evening. Turning joins away is what actually enforces
it, and it works regardless of how the server came back.

The window spans midnight correctly. Anything before the wake time belongs to
the previous evening, so 01:00 on Saturday is still Friday night.

## Controls

The page at `/bedtime` shows the countdown and three buttons.

| Control | What it does |
| --- | --- |
| **+15 minutes** | Pushes tonight's bedtime back, within `MAX_EXTENSIONS`. Warnings re-arm, so the countdown is announced again against the new deadline. |
| **Skip tonight** | Cancels bedtime for this evening only. Everything resets tomorrow. |
| **Bedtime now** | Brings it forward to right now. |

All three refuse once bedtime has already happened, and say so. A refusal comes
back as `409`, because the request was fine and the server simply will not do it.

## Configuration

Copy `config/bedtime.conf.example` to `config/bedtime.conf`. The real file is
gitignored.

| Setting | Default | Meaning |
| --- | --- | --- |
| `ENABLED` | `false` | Bedtime is off unless this says otherwise. |
| `WEEKNIGHT_BEDTIME` | `20:30` | School-night bedtime, local time. |
| `WEEKEND_BEDTIME` | `21:30` | Late bedtime. |
| `WAKE_TIME` | `07:00` | When the server opens again. |
| `WEEKEND_NIGHTS` | `friday,saturday` | Which evenings get the later time. |
| `WARN_MINUTES` | `30,15,10,5,1` | Warnings before bedtime. The largest also sets how early the bossbar appears. |
| `EXTEND_MINUTES` | `15` | Length of one extension. |
| `MAX_EXTENSIONS` | `1` | Extensions allowed per evening. `0` disables them. |
| `ACTION` | `stop` | `stop`, `kick` or `announce`. |
| `BOSSBAR` | `true` | Show the countdown bar. |

**Bedtime defaults to disabled, deliberately.** Something that can stop the
server and turn people away should never switch itself on because a default said
so.

`WEEKEND_NIGHTS` names evenings, not days. It is the night before a non-school
morning that matters, which is why it defaults to Friday and Saturday.

## REST API

`GET /api/bedtime` needs `server.view`, so a read-only account can watch the
countdown. The three controls need `server.control`.

```
GET  /api/bedtime
POST /api/bedtime/extend
POST /api/bedtime/skip
POST /api/bedtime/now
```

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/bedtime
```

The status shape is the same one the dashboard renders, so it also suits a phone
widget or a Shortcut.

## Notes

- **Warnings describe the time actually left.** A server started with ten
  minutes to go says "10 minutes until bedtime", not "30 minutes". Every mark at
  or above the remaining time is treated as given, so the larger ones do not fire
  afterwards once they no longer describe anything.
- **The join kick is queued, not sent inline.** Event bus handlers run on the
  thread that follows the server log, and sending a command makes a network call.
  The bedtime thread picks it up, normally within a few milliseconds. See
  [EVENT_BUS.md](EVENT_BUS.md).
- **All scheduling takes the current time as an argument**, so a whole evening
  can be tested without waiting for one.
- **Times are local to the server**, from the container's `TZ`.

## Related

- [EVENT_BUS.md](EVENT_BUS.md) — where join events come from
- [FAMILY_SERVER_ROADMAP.md](FAMILY_SERVER_ROADMAP.md) — W5, and what comes next
