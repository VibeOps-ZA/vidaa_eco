"""Pure idle/active decision logic for VIDAA Eco auto power-off.

Deliberately free of Home Assistant imports so it can be unit-tested directly.
The coordinator wraps these with live TV state and the throughput sensor.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple

# In-app statetypes: the TV says an app is open, but not whether it is playing,
# so network throughput decides (no throughput data -> treated as in use).
INAPP_STATETYPES: Tuple[str, ...] = ("app",)

# Live TV (aerial / cable / satellite) is decoded by the TV's own tuner and
# uses no network traffic at all, so throughput can never tell playing from
# idle. It always counts as in use, as the README promises.
LIVETV_STATETYPES: Tuple[str, ...] = ("livetv",)

# The only statetypes that are unambiguously idle: the home screen and a
# settings menu.
IDLE_STATETYPES: Tuple[str, ...] = ("remote_launcher", "remote_setting")

# What to do with a statetype this integration does not know (newer firmware,
# screen mirroring, a USB media player ...). Option "unknown_state_mode".
UNKNOWN_STATE_THROUGHPUT = "throughput"  # like an app: traffic decides (default)
UNKNOWN_STATE_IN_USE = "in_use"          # never idle
UNKNOWN_STATE_IDLE = "idle"              # always idle (behaviour before eco.10)
UNKNOWN_STATE_MODES: Tuple[str, ...] = (
    UNKNOWN_STATE_THROUGHPUT,
    UNKNOWN_STATE_IN_USE,
    UNKNOWN_STATE_IDLE,
)
DEFAULT_UNKNOWN_STATE_MODE = UNKNOWN_STATE_THROUGHPUT


def _throughput_says_active(throughput_kbps: Optional[float], floor: float) -> bool:
    """Traffic at or above the floor = playing. No data = assume playing."""
    if throughput_kbps is None:
        return True  # cannot tell playing from paused -> never cut a stream
    return throughput_kbps >= floor


def is_active(
    *,
    is_on: bool,
    statetype: Optional[str],
    is_signal,
    throughput_kbps: Optional[float],
    floor: float,
    unknown_state_mode: str = DEFAULT_UNKNOWN_STATE_MODE,
) -> bool:
    """Whether the TV is doing something a viewer would not want cut off.

    throughput_kbps is None when no throughput sensor is configured (or none
    currently has a value) - an app is then always treated as active, so a
    stream is never cut.
    """
    if not is_on:
        return False
    if statetype == "sourceswitch":
        # External input (HDMI/AV). is_signal is the integration's combined
        # signal reading for the selected input (see the coordinator):
        #   True  -> a picture is coming in: in use, no timer
        #   False -> nothing coming in: idle, the timer may run
        #   None  -> unknown: treated as in use, so a picture is never cut
        if is_signal is None:
            return True
        return bool(is_signal)
    if statetype in LIVETV_STATETYPES:
        return True
    if statetype in INAPP_STATETYPES:
        return _throughput_says_active(throughput_kbps, floor)
    if statetype in IDLE_STATETYPES:
        return False
    # A statetype we do not know. Safe default: judge it like an app.
    if unknown_state_mode == UNKNOWN_STATE_IDLE:
        return False
    if unknown_state_mode == UNKNOWN_STATE_IN_USE:
        return True
    return _throughput_says_active(throughput_kbps, floor)


def interaction_changed(previous: Optional[Sequence[Any]], current: Optional[Sequence[Any]]) -> bool:
    """True when something a viewer does shows up between two polls.

    The snapshots hold what the TV reported (statetype, app, input, channel,
    volume, mute). A field only counts when it is known in BOTH polls: a
    volume query that times out (None) must not look like someone pressing a
    button on every other poll, or an idle TV would never be switched off.
    """
    if previous is None or current is None or len(previous) != len(current):
        return False
    return any(
        old is not None and new is not None and old != new
        for old, new in zip(previous, current)
    )


class IdleTracker:
    """Two-stage idle timer: silent detect window, then a visible grace delay."""

    def __init__(self, detect_seconds: float) -> None:
        self.detect_seconds = detect_seconds
        self.idle_since: Optional[float] = None
        self.grace_deadline: Optional[float] = None
        self._last_snapshot: Optional[Sequence[Any]] = None

    def reset(self) -> None:
        self.idle_since = None
        self.grace_deadline = None

    def evaluate(
        self,
        *,
        now: float,
        enabled: bool,
        active: bool,
        delay_min: float,
        snapshot: Optional[Sequence[Any]] = None,
        vol_snapshot: Optional[Sequence[Any]] = None,
    ) -> Optional[str]:
        """Return "power_off" when the TV should be turned off, else None.

        ``snapshot`` is what the TV reported this poll (see
        :func:`interaction_changed`); any change counts as activity and resets
        both stages. ``vol_snapshot`` is the older, volume-only name for it.
        """
        if snapshot is None:
            snapshot = vol_snapshot
        if not enabled:
            self.reset()
            self._last_snapshot = snapshot
            return None

        # A channel, app, input, volume or mute change is someone at the TV.
        if interaction_changed(self._last_snapshot, snapshot):
            active = True
        if snapshot is not None:
            self._last_snapshot = snapshot

        if active:
            self.reset()
            return None

        if self.idle_since is None:
            self.idle_since = now
            return None
        if (now - self.idle_since) < self.detect_seconds:
            return None  # still inside the silent confirm-idle window

        if self.grace_deadline is None:
            self.grace_deadline = now + max(1, int(delay_min)) * 60
            return None
        if now >= self.grace_deadline:
            self.reset()
            return "power_off"
        return None
