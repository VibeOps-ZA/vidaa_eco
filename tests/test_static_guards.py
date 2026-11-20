"""Source-level guards for rules that need Home Assistant to test at runtime.

These read the integration's source (no Home Assistant needed) and fail when
a later change quietly breaks one of the rules below.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "custom_components", "vidaa_eco")


def _tree(name):
    with open(os.path.join(PKG, name), encoding="utf-8") as fh:
        return ast.parse(fh.read())


# pyvidaa calls that wait for the TV's reply. pyvidaa hands a reply to
# whichever request is waiting, so two of these must never run at once.
REQUEST_CALLS = {
    "async_get_state",
    "async_get_volume",
    "async_get_sources",
    "async_get_apps",
    "async_get_device_info",
    "async_power_off",
    "async_power_on",
}
# Coordinator methods that only ever run inside the locked poll.
POLL_ONLY = {
    "_async_update_data_locked",
    "_async_fetch_sources",
    "_async_fetch_device_info",
    "_async_maybe_refresh_token",
}


def test_every_tv_request_is_serialised():
    tree = _tree("coordinator.py")
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    unguarded = []
    for fn in cls.body:
        if not isinstance(fn, ast.AsyncFunctionDef) or fn.name in POLL_ONLY:
            continue
        locked_nodes = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.AsyncWith) and any(
                "request_lock" in ast.unparse(item.context_expr) for item in node.items
            ):
                locked_nodes.update(id(sub) for sub in ast.walk(node))
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in REQUEST_CALLS
                and ast.unparse(node.func.value) == "self.tv"
                and id(node) not in locked_nodes
            ):
                unguarded.append(f"{fn.name}: {ast.unparse(node)}")
    assert unguarded == []


def test_diagnostics_redact_network_identifiers():
    tree = _tree("diagnostics.py")
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "TO_REDACT" for t in n.targets)
    )
    keys = set(ast.literal_eval(assign.value))
    for key in ("host", "ip", "mac", "hw_mac", "mac_ethernet", "mac_wifi", "wol_mac", "device_id",
                "certfile", "keyfile", "network_type"):
        assert key in keys, key
    # Options hold wol_mac, so they are redacted too.
    src = ast.unparse(tree)
    assert "async_redact_data(dict(entry.options), TO_REDACT)" in src


def test_strings_and_english_translation_match():
    with open(os.path.join(PKG, "strings.json"), encoding="utf-8") as a, \
            open(os.path.join(PKG, "translations", "en.json"), encoding="utf-8") as b:
        assert a.read() == b.read()


def test_unknown_state_option_is_offered_and_translated():
    import json
    sys.path.insert(0, PKG)
    from idle_logic import UNKNOWN_STATE_MODES

    with open(os.path.join(PKG, "strings.json"), encoding="utf-8") as fh:
        strings = json.load(fh)
    init = strings["options"]["step"]["init"]
    assert "unknown_state_mode" in init["data"]
    assert "unknown_state_mode" in init["data_description"]
    assert set(strings["selector"]["unknown_state_mode"]["options"]) == set(UNKNOWN_STATE_MODES)
