"""Pure idle/active decision logic for VIDAA Eco auto power-off.

Deliberately free of Home Assistant imports so it can be unit-tested directly.
The coordinator wraps these with live TV state and the throughput sensor.
"""
from __future__ import annotations

from typing import Optional, Tuple

INAPP_STATETYPES: Tuple[str, ...] = ("app", "livetv")


def is_active(
    *,
    is_on: bool,
    statetype: Optional[str],
    is_signal,
    throughput_kbps: Optional[float],
    floor: float,
) -> bool:
    """Whether the TV is doing something a viewer would not want cut off.

    throughput_kbps is None when no throughput sensor is configured - in which
    case an in-app state is always treated as active, so a stream is never cut.
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
    if statetype in INAPP_STATETYPES:
        if throughput_kbps is None:
            return True  # cannot tell playing from paused -> assume active
        return throughput_kbps >= floor
    # remote_launcher, remote_setting, anything else while on -> idle.
    return False


class IdleTracker:
    """Two-stage idle timer: silent detect window, then a visible grace delay."""

    def __init__(self, detect_seconds: float) -> None:
        self.detect_seconds = detect_seconds
        self.idle_since: Optional[float] = None
        self.grace_deadline: Optional[float] = None
        self._last_vol = None

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
        vol_snapshot=None,
    ) -> Optional[str]:
        """Return "power_off" when the TV should be turned off, else None."""
        if not enabled:
            self.reset()
            self._last_vol = vol_snapshot
            return None

        # A volume/mute change is remote interaction -> activity.
        if (
            self._last_vol is not None
            and vol_snapshot is not None
            and vol_snapshot != self._last_vol
        ):
            active = True
        self._last_vol = vol_snapshot

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
