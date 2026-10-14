# VIDAA Eco

Control your **Hisense VIDAA** TV from [Home Assistant](https://www.home-assistant.io/) —
power, volume, inputs, apps and every practical remote button — and let it
**switch the TV off by itself** when it has been left on with nothing to watch.

Everything runs on your own network. No cloud account is needed.

![TV Remotes dashboard](docs/images/dashboard-study-youtube.png)

> **Built on** [ha_vidaatv](https://github.com/warrenrees/ha_vidaatv) and
> [pyvidaa](https://github.com/warrenrees/pyvidaa) by **Warren Rees**. VIDAA Eco
> is a fork that extends that work — huge thanks for the protocol
> reverse-engineering and the pairing implementation that make this possible.
> See [`NOTICE`](NOTICE).

---

## Contents

1. [What you get](#what-you-get)
2. [Before you start](#before-you-start)
3. [Install](#install)
4. [Add your TV (pairing)](#add-your-tv-pairing)
5. [Entities explained](#entities-explained)
6. [Automatic power-off explained](#automatic-power-off-explained)
7. [Options (after setup)](#options-after-setup)
8. [A remote-control dashboard](#a-remote-control-dashboard)
9. [Using it in automations and scenes](#using-it-in-automations-and-scenes)
10. [Troubleshooting](#troubleshooting)
11. [Credits & licence](#credits--licence)

---

## What you get

For every TV you add, VIDAA Eco creates one **device** in Home Assistant with:

| Entity | What it does |
|---|---|
| **TV** (media player) | On/off (including Wake-on-LAN), volume, mute, input and app selection, play/pause |
| **Remote** (remote) | Send any remote key from automations with `remote.send_command` |
| **Activity** (sensor) | What is on screen: `YouTube`, `HDMI1`, `HDMI1 – no signal`, `TV: SABC 3`, `Inactive`, `Off` |
| **Auto-off status** (sensor) | What automatic power-off is doing: `In use`, `HDMI1 in use – no timer`, `No signal – checking`, `Powering off in 12 min` … |
| **Auto power-off** (switch) | Turn automatic power-off on or off for this TV |
| **Auto-off delay** (number) | Minutes to wait (after the TV is confirmed idle) before switching it off |
| **Buttons** | One per remote key — Up, Down, Left, Right, OK, Back, Home, Menu, Exit, Info, Play, Pause, Stop, Rewind, Fast forward, Subtitles, Mute, Volume ±, Channel ±, Red, Green, Yellow, Blue |
| **App buttons** | Plex, YouTube, Netflix, Prime Video |
| **Input buttons** | One per input your TV reports — usually TV, HDMI1, HDMI2, HDMI3, AV |

Buttons are greyed out while the TV is off (it cannot receive keys until it is on).

---

## Before you start

You need:

1. **Home Assistant** — any installation type. New to it? Start at
   [home-assistant.io/installation](https://www.home-assistant.io/installation/).
2. **HACS** (the Home Assistant Community Store) — the easiest way to install and
   update custom integrations like this one. Install it by following
   [hacs.xyz/docs/use](https://hacs.xyz/docs/use/).
3. **A Hisense / VIDAA TV on the same network** as Home Assistant, switched on
   for the first setup. Give it a fixed IP address in your router (a "DHCP
   reservation") so Home Assistant can always find it.
4. **The VIDAA client certificate** — two small files, `vidaa_client.pem` and
   `vidaa_client.key`. Most VIDAA TVs only accept connections from the official
   app, which proves itself with this certificate. It belongs to Hisense, so it
   is **not** included here; the upstream project explains how to extract it
   from the official VIDAA app: see
   [ha_vidaatv → Obtaining the client certificate](https://github.com/warrenrees/ha_vidaatv#readme).
   Copy both files into a folder called **`certs`** inside your Home Assistant
   configuration folder (so you end up with `config/certs/vidaa_client.pem` and
   `config/certs/vidaa_client.key`). The
   [File editor](https://www.home-assistant.io/common-tasks/os/#installing-and-using-the-file-editor-app)
   or [Samba share](https://github.com/home-assistant/addons/blob/master/samba/DOCS.md)
   apps make this easy.
   *Some older TVs speak plain MQTT and need no certificate — see
   [Use SSL/TLS](#add-your-tv-pairing) below.*
5. **Optional – Wake-on-LAN enabled on the TV** so Home Assistant can switch it
   *on* (switching off always works). On most VIDAA TVs: **Settings → Network →
   Wake on LAN** (sometimes called *Wake on Wireless Network*).

---

## Install

### Option A — HACS (recommended)

1. Open **HACS** in the Home Assistant sidebar.
2. Open the menu (⋮, top right) → **Custom repositories**.
3. Paste `https://github.com/VibeOps-ZA/vidaa_eco`, choose type
   **Integration**, click **Add**.
   ([What is a custom repository?](https://hacs.xyz/docs/faq/custom_repositories/))
4. Search HACS for **VIDAA Eco**, open it, click **Download**.
5. **Restart Home Assistant**: **Settings → System → ⏻ (top right) → Restart Home Assistant**.

### Option B — Manual

1. Download this repository (green **Code** button → **Download ZIP**).
2. Copy the folder `custom_components/vidaa_eco` into your Home Assistant
   `config/custom_components/` folder (create `custom_components` if it doesn't exist).
3. Restart Home Assistant.

---

## Add your TV (pairing)

1. **Switch the TV on** and leave it on the home screen.
2. In Home Assistant go to **Settings → Devices & services**.
   - If the TV shows under **Discovered**, click **Add** next to it.
   - Otherwise click **+ Add integration**, search for **VIDAA Eco**, and enter:
     - **Host** – the TV's IP address (e.g. `192.168.1.50`).
     - **Port** – leave as `36669`.
3. **Certificates** step:
   - **Use SSL/TLS** – leave **on** for almost every TV. Turn it off only if setup
     fails to connect and your TV is older firmware that speaks plain MQTT; then
     no certificate is needed.
   - **Certificate file path / Key file path** – leave the defaults if you placed
     the files in `config/certs/` as above.
   - **Authentication mode** – leave on **Auto**. It detects your TV's protocol
     and falls back automatically. Choose **Static** only if an older TV fails
     with a "not authorised" error; **Dynamic** forces the newer scheme.
4. Click **Submit** and **be patient** — talking to the TV can take up to a
   minute while it tries the right connection method.
5. A **4-digit PIN appears on the TV**. Type it into Home Assistant and submit.
6. Done. Pick the room (area) the TV is in, and the device and its entities appear.

Repeat for each TV.

---

## Entities explained

Entity IDs are built from the TV's name. For a TV called *Study TV* you get
`media_player.study_tv`, `sensor.study_tv_activity`, `button.study_tv_ok` and so on.

### Activity sensor

| Shows | Meaning |
|---|---|
| `YouTube`, `Netflix`, … | That app is open |
| `HDMI1` | That input is selected and a picture is coming in |
| `HDMI1 – no signal` | That input is selected but nothing is connected / the device is asleep |
| `TV: <channel>` | Watching live TV |
| `Inactive` | Home screen or a settings menu |
| `Off` | TV is off |

Attributes include `statetype` (the TV's raw state), `source`, `channel_name`,
`signal` (`yes`/`no` on an input) and `signal_detail` (the raw signal flags for
every input — handy for troubleshooting).

### Auto-off status sensor

| Shows | Meaning |
|---|---|
| `Off` | TV is off |
| `Auto-off disabled` | The **Auto power-off** switch is off |
| `In use` | Something is on that you would not want switched off |
| `HDMI1 in use – no timer` | On an input with a picture coming in — never counts down |
| `Idle – checking` / `No signal – checking` | Looks idle; the 15-minute confirmation window is running |
| `Powering off in N min` | Idle confirmed; your delay is counting down |

For automations use its `status` attribute, which never changes wording:
`off`, `disabled`, `active`, `hdmi`, `idle`, `countdown`. Other attributes:
`idle_since`, `idle_minutes`, `minutes_remaining`, `power_off_at`.

![Auto-off status history](docs/images/auto-off-more-info.png)

---

## Automatic power-off explained

Off by default — switch **Auto power-off** on for each TV you want it on.

It works in two stages so it never surprises you:

1. **Confirm idle (15 minutes, fixed).** The TV has to look idle the whole time.
2. **Your delay.** Only then does **Auto-off delay** start counting. If the TV is
   still idle when it reaches zero, it is switched off.

So with the delay set to 30, an idle TV goes off **15 + 30 = 45 minutes** after
it went idle. Anything that counts as activity — changing channel, opening an
app, a picture appearing on an input, even a volume or mute change — resets both
stages. If the TV is switched off some other way before the countdown ends, the
timer simply clears.

![Counting down on the dashboard](docs/images/dashboard-study-countdown.png)

**What counts as idle**

| Situation | Idle? |
|---|---|
| Home screen or a settings menu | Yes |
| An HDMI / AV input with **no signal** (nothing connected, or the device is asleep) | Yes. Many TVs also switch themselves to standby after ~15 minutes with no signal — whichever comes first wins. |
| An HDMI / AV input with a **picture coming in** | **No** — shows "*input* in use – no timer". The TV can't tell whether you are watching a connected device, so let that device sleep (most do, and HDMI-CEC can switch the TV off with it). |
| Live TV | No |
| Inside an app (YouTube, Plex, …) | No — unless you add a throughput sensor (below) |

**How "signal" is detected.** The TV reports a signal flag for every input
(`has_signal`) each time it is asked, plus a snapshot taken at the moment you
switch input. VIDAA Eco asks every poll while an input is selected and treats
the input as in use if either says a picture is present. The input's other flag
(`is_signal`) only marks which input is selected, so it is not used.

### In-app detection with a throughput sensor (optional)

Inside an app, the TV reports the same thing whether a film is playing or
paused, so by default VIDAA Eco **never switches off while an app is open**. If
you give it a sensor with the TV's current network traffic, it can tell: below
the **floor** (e.g. 100 kbit/s) means nothing is streaming, so the app counts as idle.

Any sensor reporting this TV's traffic **in kbit/s** works, for example:

- **UniFi** – the [UniFi Network integration](https://www.home-assistant.io/integrations/unifi/)
  can expose per-client bandwidth sensors; pick the TV's receive (RX) sensor.
- **Router / access point via SNMP** – read the TV's byte counter with the
  [SNMP integration](https://www.home-assistant.io/integrations/snmp/) and turn it
  into a rate with a [Derivative helper](https://www.home-assistant.io/integrations/derivative/).
- **Router integrations** that already publish client throughput (e.g.
  [MikroTik](https://www.home-assistant.io/integrations/mikrotik/)).

Set it in the TV's options (next section).

---

## Options (after setup)

**Settings → Devices & services → VIDAA Eco → Configure** on the TV:

| Option | What it does | Default |
|---|---|---|
| **Polling interval** | How often (seconds) to ask the TV what it is doing | 30 |
| **Wake-on-LAN MAC address** | Where to send the "wake up" packet. The TV's Ethernet and Wi-Fi addresses are listed in the dialog — if switching on doesn't work, try the other one | The TV's own |
| **Authentication mode** | Override the scheme chosen at pairing (Auto / Dynamic / Static). Only change if the TV starts refusing connections after a firmware update | As paired |
| **Throughput sensor** | Optional sensor with the TV's network rate in kbit/s (see above) | None |
| **Throughput floor** | Below this rate (kbit/s) an open app counts as "nothing streaming" | 100 |

The **Auto power-off** switch and **Auto-off delay** number are ordinary
entities, so you can change them from a dashboard or an automation.

---

## A remote-control dashboard

A ready-made, remote-style dashboard using only Home Assistant's built-in cards
is in [`docs/dashboard.md`](docs/dashboard.md) — step-by-step instructions plus
the YAML to paste.

| Desktop | Phone |
|---|---|
| ![Desktop](docs/images/dashboard-study-no-signal.png) | ![Phone](docs/images/dashboard-study-mobile.png) |

---

## Using it in automations and scenes

Every button is a normal `button` entity, so in the automation editor choose
**Action → Button: Press** and pick e.g. `button.study_tv_hdmi1`.

```yaml
# Switch to HDMI 1 when the PlayStation turns on
actions:
  - action: button.press
    target:
      entity_id: button.study_tv_hdmi1
```

```yaml
# Tell me when a TV is about to switch itself off
triggers:
  - trigger: state
    entity_id: sensor.study_tv_auto_off_status
    attribute: status
    to: countdown
actions:
  - action: notify.notify
    data:
      message: "Study TV will switch off in {{ state_attr('sensor.study_tv_auto_off_status', 'minutes_remaining') }} min"
```

Other ways to control the TV:

- **Media player actions** – `media_player.turn_on`, `turn_off`, `volume_set`,
  `select_source` (inputs and app names from the TV's list).
- **Remote** – `remote.send_command` with any key, e.g. `KEY_OK`, `KEY_RETURNS`.

---

## Troubleshooting

| Problem | Try |
|---|---|
| Setup spins for a long time | Normal for up to a minute. Make sure the TV is on and awake. |
| No PIN appears on the TV | The TV must be on its home screen. Close the dialog, wait 30 s, try again. |
| "Certificate files not found" | Check the files are in `config/certs/` with exactly the names `vidaa_client.pem` and `vidaa_client.key`. |
| Can switch off but not on | Enable Wake-on-LAN on the TV, then try the other MAC address in the options. |
| Buttons greyed out | The TV is off — buttons only work while it is on. |
| Auto-off never counts down | Check the switch is on; on an input it only counts down with **no signal**; in an app only with a throughput sensor. The Activity sensor's `signal_detail` attribute shows what the TV reports. |
| Need more detail | **Settings → Devices & services → VIDAA Eco → ⋮ → Enable debug logging**, reproduce, then download the log. |

---

## Credits & licence

Fork of [ha_vidaatv](https://github.com/warrenrees/ha_vidaatv) /
[pyvidaa](https://github.com/warrenrees/pyvidaa) by Warren Rees. MIT licensed —
see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). Not affiliated with Hisense or VIDAA.
