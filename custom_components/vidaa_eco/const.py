"""Constants for the Hisense TV integration."""

from typing import Final

DOMAIN: Final = "vidaa_eco"

# Configuration keys
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_MAC: Final = "mac"
# The TV's real hardware MAC, only ever set from the TV's own descriptor.
# Distinct from CONF_MAC, which for dynamic auth may hold a random placeholder
# used to build a client_id - sending Wake-on-LAN to that would do nothing.
CONF_HW_MAC: Final = "hw_mac"
# Per-interface MACs. The descriptor does not say which interface the TV is
# actually connected on, and Wake-on-LAN only works against that one, so both
# are surfaced for the user to choose between.
CONF_MAC_ETHERNET: Final = "mac_ethernet"
CONF_MAC_WIFI: Final = "mac_wifi"
CONF_NAME: Final = "name"
CONF_DEVICE_ID: Final = "device_id"
CONF_MODEL: Final = "model"
CONF_BRAND: Final = "brand"
CONF_SW_VERSION: Final = "sw_version"
CONF_CERTFILE: Final = "certfile"
CONF_KEYFILE: Final = "keyfile"
# Whether to connect over SSL/TLS. Some older TVs (transport_protocol < 1001)
# expose a plain, unencrypted MQTT broker on the same port and reset the
# connection on any TLS ClientHello, so mTLS can never succeed against them.
# Turning this off lets those TVs pair without client certificates.
CONF_USE_SSL: Final = "use_ssl"
CONF_AUTH_MODE: Final = "auth_mode"
# The TV's physical inputs (TV, HDMI1.., AV), remembered from its source list so
# the input buttons exist even while the TV is off.
CONF_INPUTS: Final = "inputs"

# Credential scheme. "auto" detects the TV's protocol version and falls back
# through the other methods if it rejects the credentials; "static" forces the
# fixed login that pre-dynamic firmware (transport_protocol < 3000) needs;
# "dynamic" forces the timestamp-hash algorithm. Entries created before this
# option existed have no value stored and are treated as "auto".
AUTH_MODE_AUTO: Final = "auto"
AUTH_MODE_DYNAMIC: Final = "dynamic"
AUTH_MODE_STATIC: Final = "static"
AUTH_MODES: Final = [AUTH_MODE_AUTO, AUTH_MODE_DYNAMIC, AUTH_MODE_STATIC]

# Default values
DEFAULT_PORT: Final = 36669
DEFAULT_NAME: Final = "Hisense TV"
DEFAULT_AUTH_MODE: Final = AUTH_MODE_AUTO
# Most TVs speak MQTT over TLS; plain MQTT is the exception, so default to on.
DEFAULT_USE_SSL: Final = True

# Default certificate paths (relative to HA config directory)
DEFAULT_CERT_DIR: Final = "certs"
DEFAULT_CERT_FILENAME: Final = "vidaa_client.pem"
DEFAULT_KEY_FILENAME: Final = "vidaa_client.key"

# Timeouts
TIMEOUT_CONNECT: Final = 10
TIMEOUT_COMMAND: Final = 5
TIMEOUT_DISCOVERY: Final = 5
# How long to wait for the TV to confirm the pairing PIN is on screen
TIMEOUT_PIN_DIALOG: Final = 8

# Scan interval for polling
SCAN_INTERVAL: Final = 30

# Services
SERVICE_SEND_KEY: Final = "send_key"
SERVICE_LAUNCH_APP: Final = "launch_app"

# Attributes
ATTR_KEY: Final = "key"
ATTR_APP: Final = "app"

# States
# The statetype a TV reports while in standby. Match it EXACTLY: the trailing
# digit is a direction, not a sleep depth. Captured from a real TV, pressing
# power sends fake_sleep_0 going into standby and fake_sleep_1 coming out of it
# (immediately followed by remote_launcher), so treating "fake_sleep*" as
# asleep would report the TV off at the moment it is being switched on.
STATE_FAKE_SLEEP: Final = "fake_sleep_0"
STATE_REMOTE_LAUNCHER: Final = "remote_launcher"  # TV at the home screen

# Remote activity shown when the TV is on its home screen / launcher
ACTIVITY_HOME: Final = "Home"

# Platform types
PLATFORMS: Final = ["media_player", "remote", "number", "switch", "sensor", "button"]


# --- VIDAA Eco: automatic power-off (idle / sleep detection) ---
# Stored in entry.options (throughput) and held on the coordinator (enable/delay,
# driven by the switch/number entities).
CONF_AUTO_OFF_ENABLED: Final = "auto_off_enabled"
CONF_AUTO_OFF_DELAY: Final = "auto_off_delay"          # grace MINUTES after idle confirmed
CONF_THROUGHPUT_SENSOR: Final = "throughput_sensor"    # optional entity_id, rate in kbit/s
CONF_THROUGHPUT_FLOOR: Final = "throughput_floor_kbps" # below this = "nothing streaming"
CONF_THROUGHPUT_SENSORS: Final = "throughput_sensors"  # list of entity_ids, summed (replaces the single one)
CONF_THROUGHPUT_AUTO: Final = "throughput_auto"        # find sensors on HA devices sharing the TV's MAC
DEFAULT_THROUGHPUT_AUTO: Final = True
# Re-scan the device/entity registries for auto-detected sources this often.
THROUGHPUT_DISCOVERY_SECONDS: Final = 300
# Where the README explains throughput sources (linked from options, repairs, errors).
DOCS_THROUGHPUT_URL: Final = "https://github.com/VibeOps-ZA/vidaa_eco#network-throughput-for-auto-power-off"
ISSUE_THROUGHPUT_MISSING: Final = "throughput_missing"

DEFAULT_AUTO_OFF_ENABLED: Final = False   # opt-in: never power off a TV unless asked
DEFAULT_AUTO_OFF_DELAY: Final = 45        # minutes of grace AFTER idle is confirmed
DETECT_MINUTES: Final = 15                # silent confirm-idle window (not user-visible)
DEFAULT_THROUGHPUT_FLOOR: Final = 100     # kbit/s

# statetypes that are unambiguously idle - safe to power off with no throughput data
IDLE_STATETYPES: Final = ["remote_launcher", "remote_setting"]
# in-app statetypes where playing-vs-idle can only be told apart with throughput
INAPP_STATETYPES: Final = ["app", "livetv"]

# Eco state sensor values (sensor.<tv>_eco_state), in rough lifecycle order.
ECO_STATE_OFF: Final = "off"            # TV is off / unreachable
ECO_STATE_DISABLED: Final = "disabled"  # TV on, auto power-off switch is off
ECO_STATE_ACTIVE: Final = "active"      # something a viewer would miss is on
ECO_STATE_HDMI: Final = "hdmi"          # on an HDMI/external input: always in use, no timer
ECO_STATE_IDLE: Final = "idle"          # looks idle; silent confirm window running
ECO_STATE_COUNTDOWN: Final = "countdown"  # idle confirmed; user grace delay running
ECO_STATES: Final = [
    ECO_STATE_OFF, ECO_STATE_DISABLED, ECO_STATE_ACTIVE, ECO_STATE_HDMI, ECO_STATE_IDLE, ECO_STATE_COUNTDOWN,
]
