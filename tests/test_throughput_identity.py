"""Unit tests for throughput unit handling and TV identity (no HA deps)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "custom_components", "vidaa_eco"))
import throughput as tp  # noqa: E402
from identity import bare_mac, is_valid_device_id, tv_device_id  # noqa: E402


def test_to_kbps_units():
    assert tp.to_kbps("1.6", "MB/s") == 1.6 * 8000
    assert tp.to_kbps(13, "Mbit/s") == 13000
    assert tp.to_kbps(500, "kbit/s") == 500
    assert tp.to_kbps(500, None) == 500          # legacy: unitless = kbit/s
    assert tp.to_kbps(2000, "B/s") == 16
    assert tp.to_kbps("abc", "MB/s") is None
    assert tp.to_kbps(1, "W") is None            # not a data rate


def test_configured_sources_merges_legacy():
    assert tp.configured_sources({}) == []
    assert tp.configured_sources({"throughput_sensor": "sensor.a"}) == ["sensor.a"]
    assert tp.configured_sources({"throughput_sensors": ["sensor.b", "sensor.a"], "throughput_sensor": "sensor.a"}) == ["sensor.b", "sensor.a"]


def test_tv_macs():
    macs = tp.tv_macs({"mac": "00:00:5E:00:53:AA", "mac_wifi": "00:00:5e:00:53:6e", "device_id": "wlan"})
    assert macs == {"00:00:5e:00:53:aa", "00:00:5e:00:53:6e"}
    assert tp.tv_macs({"device_id": "00005e0053d4"}) == {"00:00:5e:00:53:d4"}


def test_identity():
    assert bare_mac("00:00:5E:00:53:D4") == "00005e0053d4"
    assert bare_mac("wlan") is None
    assert is_valid_device_id("00005e0053d4") and not is_valid_device_id("wlan")
    assert tv_device_id({"network_type": "00005e0053d4"}, "aa:aa:aa:aa:aa:aa") == "00005e0053d4"
    assert tv_device_id({"network_type": "wlan"}, None, "00:00:5e:00:53:6e") == "00005e00536e"
    assert tv_device_id({"network_type": "wlan"}) is None
