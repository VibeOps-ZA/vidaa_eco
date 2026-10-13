# VIDAA Eco

Home Assistant integration for Hisense **VIDAA** TVs — full local control, plus
**automatic power-off when the TV is left on with nothing playing**.

> **Built on** [ha_vidaatv](https://github.com/warrenrees/ha_vidaatv) and
> [pyvidaa](https://github.com/warrenrees/pyvidaa) by **Warren Rees**. VIDAA Eco
> is a fork that extends that excellent work — huge thanks for the protocol
> reverse-engineering and the pairing implementation that make this possible.
> See [`NOTICE`](NOTICE).

## Why this exists

The upstream integration is great at *controlling* a VIDAA TV. What it doesn't do
is notice when you've fallen asleep with YouTube or Plex still open and quietly
turn the TV off. VIDAA Eco adds exactly that, and folds it into a single
integration so there's **one thing to maintain and no risk of an external update
breaking a working setup**. It also:

- **Hardens device identity** to stop the duplicate-device problem (it anchors on
  the TV's hardware MAC instead of switching identifiers after pairing).
- **Surfaces the HDMI `is_signal` flag** the TV already reports (so "my laptop
  went to sleep on HDMI" is detectable).
- Keeps full VIDAA control: power (incl. Wake-on-LAN), volume, sources, apps,
  all remote keys, playback.

Protocol-level improvements are intended to flow **back upstream**; the power-save
behaviour is what lives here.

## How the auto power-off works

Per TV you get two entities (both opt-in; **off by default**):

- **Auto power-off** (switch) — enable the feature.
- **Auto-off delay** (number, minutes) — your grace period.
- **Eco state** (sensor) — what the logic currently thinks: `Off`, `Disabled`,
  `Active`, `Idle` (silent confirm window) or `Counting down` (your grace delay
  is running; `minutes_remaining` / `power_off_at` attributes say when).
- **Activity** (sensor) — what is on screen: app name, input (e.g. `HDMI1`),
  `TV: <channel>`, `Inactive` at the home screen/settings, `Off`.
- **Buttons** — one per remote key (Up/Down/Left/Right/OK, Back, Home, Menu,
  Exit, Info, Play, Pause, Stop, Rewind, Fast forward, Subtitles, Mute,
  Volume ±, Channel ±, Red/Green/Yellow/Blue) and app launchers (Plex, YouTube,
  Netflix, Prime Video). Unavailable while the TV is off.

An HDMI/external input always counts as in use: the TV cannot report whether a
live picture is present, so a TV left on an input is never powered off by this
integration - let the source device put it to sleep (e.g. HDMI-CEC).

The logic is two-stage and deliberate:

1. The TV must look **idle** continuously for a fixed **15-minute detection
   window** (silent — not shown anywhere).
2. *Then* your **Auto-off delay** starts counting. When it elapses still-idle,
   the TV is powered off.

So with the delay set to 45, the TV sits idle **15 + 45 = 60 minutes** before it
turns off. The 15 is an intentional buffer and is never folded into the number
you set.

"Idle" means: off, home screen, a settings menu, or an HDMI input with **no
signal**. Inside an app (YouTube/Plex/etc.) the TV reports the same state whether
something is playing or paused — so to tell those apart, VIDAA Eco uses an
optional **throughput sensor** (below). **Without a throughput sensor it will
never power off while an app is open**, so it can't cut a stream you're watching.

## Providing a throughput sensor (optional, enables in-app detection)

Point the integration at any sensor that reports this TV's current network
**rate in kbit/s** (Options → *Throughput sensor*). Any box on the TV's network
path can provide it:

1. **UniFi** — enable the UniFi integration's per-client bandwidth sensors and
   select the TV's RX sensor. (Easiest if you run UniFi.)
2. **SNMP (router *or* access point)** — most routers and managed/controller APs
   (UDM, pfSense/OPNsense, Mikrotik, **Ruckus**, Omada, Aruba…) expose per-client
   or per-port byte counters over SNMP. Read the counter with HA's SNMP
   integration and convert it to a rate with a **`derivative` helper**.
3. **Router/AP-specific integrations** — Mikrotik, OPNsense, AsusWRT, etc. already
   publish client throughput sensors; just pick the entity.
4. **NetFlow / sFlow** — if your gear exports flows, a collector can publish
   per-client rates.
5. **Nothing** — the integration still works; it just won't auto-off while an app
   is open (the safe fallback above).

It doesn't matter *which* device reports it — router, switch or AP — as long as
something the TV's traffic passes through can see that client's rate. The
integration just wants one rate sensor; set the **floor** (kbit/s below which
"nothing is streaming") to taste.

## Running alongside the upstream integration

VIDAA Eco uses its own domain (`vidaa_eco`) and its own device namespace, so it
can be installed **next to** `vidaa_tv` and tested in parallel before you remove
the original. Your existing certificate in `config/certs/` is reused.

## Obtaining the client certificate

Same as upstream: the VIDAA client certificate is **not** shipped (it belongs to
Hisense). Extract it from the official VIDAA/RemoteNOW app and place
`vidaa_client.pem` + `vidaa_client.key` in `config/certs/`. See the upstream
README's "Obtaining the client certificate" section.

## Credits & license

Fork of [ha_vidaatv](https://github.com/warrenrees/ha_vidaatv) /
[pyvidaa](https://github.com/warrenrees/pyvidaa) by Warren Rees. MIT licensed —
see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
