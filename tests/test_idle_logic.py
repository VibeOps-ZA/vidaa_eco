"""Unit tests for VIDAA Eco's pure idle/active decision logic (no HA deps)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "custom_components", "vidaa_eco"))
from idle_logic import (  # noqa: E402
    IdleTracker,
    UNKNOWN_STATE_IDLE,
    UNKNOWN_STATE_IN_USE,
    UNKNOWN_STATE_THROUGHPUT,
    interaction_changed,
    is_active,
)

F = 100  # floor kbit/s


def test_is_active():
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=5000, floor=F) is True
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=10, floor=F) is False
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=None, floor=F) is True
    assert is_active(is_on=True, statetype="livetv", is_signal=None, throughput_kbps=5000, floor=F) is True
    assert is_active(is_on=True, statetype="sourceswitch", is_signal=1, throughput_kbps=None, floor=F) is True
    assert is_active(is_on=True, statetype="sourceswitch", is_signal=0, throughput_kbps=None, floor=F) is False
    assert is_active(is_on=True, statetype="sourceswitch", is_signal=None, throughput_kbps=None, floor=F) is True
    assert is_active(is_on=True, statetype="remote_launcher", is_signal=None, throughput_kbps=None, floor=F) is False
    assert is_active(is_on=True, statetype="remote_setting", is_signal=None, throughput_kbps=None, floor=F) is False
    assert is_active(is_on=False, statetype="app", is_signal=None, throughput_kbps=5000, floor=F) is False


def test_live_tv_is_always_in_use():
    # Aerial/satellite TV has no network traffic: never idle, whatever the sensor says.
    for kbps in (None, 0, 5, F - 1, F, 50_000):
        assert is_active(is_on=True, statetype="livetv", is_signal=None, throughput_kbps=kbps, floor=F) is True


def test_unknown_state_default_is_judged_by_throughput():
    assert is_active(is_on=True, statetype="mirroring", is_signal=None, throughput_kbps=5000, floor=F) is True
    assert is_active(is_on=True, statetype="mirroring", is_signal=None, throughput_kbps=10, floor=F) is False
    # No throughput data -> never cut it off.
    assert is_active(is_on=True, statetype="mirroring", is_signal=None, throughput_kbps=None, floor=F) is True
    assert is_active(is_on=True, statetype=None, is_signal=None, throughput_kbps=None, floor=F) is True


def test_unknown_state_modes():
    kw = dict(is_on=True, statetype="mirroring", is_signal=None, floor=F)
    assert is_active(**kw, throughput_kbps=10, unknown_state_mode=UNKNOWN_STATE_THROUGHPUT) is False
    assert is_active(**kw, throughput_kbps=10, unknown_state_mode=UNKNOWN_STATE_IN_USE) is True
    assert is_active(**kw, throughput_kbps=5000, unknown_state_mode=UNKNOWN_STATE_IDLE) is False
    # The option never changes how known states are judged.
    for mode in (UNKNOWN_STATE_THROUGHPUT, UNKNOWN_STATE_IN_USE, UNKNOWN_STATE_IDLE):
        assert is_active(is_on=True, statetype="livetv", is_signal=None, throughput_kbps=0, floor=F,
                         unknown_state_mode=mode) is True
        assert is_active(is_on=True, statetype="remote_launcher", is_signal=None, throughput_kbps=None,
                         floor=F, unknown_state_mode=mode) is False


def test_two_stage_timer():
    DETECT, DELAY = 900, 45
    t = IdleTracker(DETECT)
    assert t.evaluate(now=0, enabled=True, active=False, delay_min=DELAY) is None
    assert t.evaluate(now=899, enabled=True, active=False, delay_min=DELAY) is None
    assert t.grace_deadline is None
    assert t.evaluate(now=901, enabled=True, active=False, delay_min=DELAY) is None
    assert t.grace_deadline is not None
    assert t.evaluate(now=901 + DELAY*60 - 1, enabled=True, active=False, delay_min=DELAY) is None
    assert t.evaluate(now=901 + DELAY*60, enabled=True, active=False, delay_min=DELAY) == "power_off"


def test_activity_resets():
    t = IdleTracker(900)
    t.evaluate(now=0, enabled=True, active=False, delay_min=45)
    t.evaluate(now=800, enabled=True, active=False, delay_min=45)
    assert t.evaluate(now=850, enabled=True, active=True, delay_min=45) is None
    assert t.idle_since is None


def test_volume_change_is_activity():
    t = IdleTracker(900)
    t.evaluate(now=0, enabled=True, active=False, delay_min=45, vol_snapshot=(20, False))
    assert t.evaluate(now=500, enabled=True, active=False, delay_min=45, vol_snapshot=(25, False)) is None
    assert t.idle_since is None


def _snap(statetype="remote_launcher", app=None, source="Home", ch_num=None, ch_name=None, vol=20, muted=False):
    return (statetype, app, source, ch_num, ch_name, vol, muted)


def test_channel_app_and_input_changes_are_activity():
    for before, after in (
        (_snap("livetv", source="TV", ch_num="5", ch_name="A"), _snap("livetv", source="TV", ch_num="6", ch_name="B")),
        (_snap("app", app="YouTube", source="YouTube"), _snap("app", app="Netflix", source="Netflix")),
        (_snap("sourceswitch", source="HDMI1"), _snap("sourceswitch", source="HDMI2")),
        (_snap("remote_launcher"), _snap("remote_setting")),
        (_snap(muted=False), _snap(muted=True)),
    ):
        t = IdleTracker(900)
        t.evaluate(now=0, enabled=True, active=False, delay_min=45, snapshot=before)
        t.evaluate(now=600, enabled=True, active=False, delay_min=45, snapshot=before)
        assert t.idle_since == 0
        t.evaluate(now=700, enabled=True, active=False, delay_min=45, snapshot=after)
        assert t.idle_since is None, (before, after)


def test_unknown_fields_are_not_activity():
    # A volume query that times out (None) every other poll must not keep an idle TV on.
    assert interaction_changed(_snap(vol=20), _snap(vol=None)) is False
    assert interaction_changed(_snap(vol=None), _snap(vol=20)) is False
    assert interaction_changed(None, _snap()) is False
    assert interaction_changed(_snap(), _snap()) is False
    t = IdleTracker(900)
    for i, vol in enumerate((20, None, 20, None, 20)):
        t.evaluate(now=i * 30, enabled=True, active=False, delay_min=45, snapshot=_snap(vol=vol))
    assert t.idle_since == 0


def test_disabled_never_fires():
    t = IdleTracker(1)
    assert t.evaluate(now=0, enabled=False, active=False, delay_min=1) is None
    assert t.evaluate(now=1000, enabled=False, active=False, delay_min=1) is None
    assert t.grace_deadline is None
