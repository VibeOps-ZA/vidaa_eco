"""Unit tests for VIDAA Eco's pure idle/active decision logic (no HA deps)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "custom_components", "vidaa_eco"))
from idle_logic import is_active, IdleTracker  # noqa: E402

F = 100  # floor kbit/s

def test_is_active():
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=5000, floor=F) is True
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=10, floor=F) is False
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=None, floor=F) is True
    assert is_active(is_on=True, statetype="livetv", is_signal=None, throughput_kbps=5000, floor=F) is True
    assert is_active(is_on=True, statetype="sourceswitch", is_signal=1, throughput_kbps=None, floor=F) is True
    assert is_active(is_on=True, statetype="sourceswitch", is_signal=0, throughput_kbps=None, floor=F) is False
    assert is_active(is_on=True, statetype="remote_launcher", is_signal=None, throughput_kbps=None, floor=F) is False
    assert is_active(is_on=True, statetype="remote_setting", is_signal=None, throughput_kbps=None, floor=F) is False
    assert is_active(is_on=False, statetype="app", is_signal=None, throughput_kbps=5000, floor=F) is False

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

def test_disabled_never_fires():
    t = IdleTracker(1)
    assert t.evaluate(now=0, enabled=False, active=False, delay_min=1) is None
    assert t.evaluate(now=1000, enabled=False, active=False, delay_min=1) is None
    assert t.grace_deadline is None
