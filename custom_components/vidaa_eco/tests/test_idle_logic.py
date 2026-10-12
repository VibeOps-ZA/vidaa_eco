import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from idle_logic import is_active, IdleTracker

F = 100  # floor kbit/s

def test_is_active():
    # streaming in an app with throughput above floor
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=5000, floor=F) is True
    # paused in an app (throughput collapsed)
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=10, floor=F) is False
    # in an app but NO throughput sensor -> must assume active (never cut a stream)
    assert is_active(is_on=True, statetype="app", is_signal=None, throughput_kbps=None, floor=F) is True
    # livetv behaves like app
    assert is_active(is_on=True, statetype="livetv", is_signal=None, throughput_kbps=5000, floor=F) is True
    # HDMI with a live signal
    assert is_active(is_on=True, statetype="sourceswitch", is_signal=1, throughput_kbps=None, floor=F) is True
    # HDMI, source asleep (no signal)
    assert is_active(is_on=True, statetype="sourceswitch", is_signal=0, throughput_kbps=None, floor=F) is False
    # sitting on the home screen / settings
    assert is_active(is_on=True, statetype="remote_launcher", is_signal=None, throughput_kbps=None, floor=F) is False
    assert is_active(is_on=True, statetype="remote_setting", is_signal=None, throughput_kbps=None, floor=F) is False
    # off
    assert is_active(is_on=False, statetype="app", is_signal=None, throughput_kbps=5000, floor=F) is False

def test_two_stage_timer():
    DETECT = 900          # 15 min
    DELAY = 45            # minutes
    t = IdleTracker(DETECT)
    # idle begins
    assert t.evaluate(now=0, enabled=True, active=False, delay_min=DELAY) is None
    # still inside detect window
    assert t.evaluate(now=899, enabled=True, active=False, delay_min=DELAY) is None
    assert t.grace_deadline is None
    # detect window passed -> grace starts (no power-off yet)
    assert t.evaluate(now=901, enabled=True, active=False, delay_min=DELAY) is None
    assert t.grace_deadline is not None
    # just before grace elapses
    assert t.evaluate(now=901 + DELAY*60 - 1, enabled=True, active=False, delay_min=DELAY) is None
    # grace elapsed -> power off
    assert t.evaluate(now=901 + DELAY*60, enabled=True, active=False, delay_min=DELAY) == "power_off"

def test_activity_resets():
    t = IdleTracker(900)
    t.evaluate(now=0, enabled=True, active=False, delay_min=45)
    t.evaluate(now=800, enabled=True, active=False, delay_min=45)
    # activity before detect completes -> reset
    assert t.evaluate(now=850, enabled=True, active=True, delay_min=45) is None
    assert t.idle_since is None

def test_volume_change_is_activity():
    t = IdleTracker(900)
    # establish baseline volume
    t.evaluate(now=0, enabled=True, active=False, delay_min=45, vol_snapshot=(20, False))
    # idle but a volume change lands -> treated as activity, timer resets
    r = t.evaluate(now=500, enabled=True, active=False, delay_min=45, vol_snapshot=(25, False))
    assert r is None and t.idle_since is None

def test_disabled_never_fires():
    t = IdleTracker(1)  # tiny detect window
    assert t.evaluate(now=0, enabled=False, active=False, delay_min=1) is None
    assert t.evaluate(now=1000, enabled=False, active=False, delay_min=1) is None
    assert t.grace_deadline is None

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
    print("ALL TESTS PASSED")
