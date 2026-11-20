"""Reload behaviour (Home Assistant 2026.12 deprecation) - no HA needed.

From Home Assistant 2026.12 an entry with an update listener is no longer
reloaded by Home Assistant when discovery stores a new TV address, so the TV
would not reconnect until a restart. VIDAA Eco must therefore use
OptionsFlowWithReload and register NO update listener on current versions.
"""
import ast
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "custom_components", "vidaa_eco")
sys.path.insert(0, PKG)
from reload_compat import (  # noqa: E402
    has_reloading_options_flow,
    needs_update_listener,
    options_flow_base,
)


class _OptionsFlow:  # stand-ins for homeassistant.config_entries classes
    pass


class _OptionsFlowWithReload(_OptionsFlow):
    automatic_reload = True


NEW_HA = SimpleNamespace(OptionsFlow=_OptionsFlow, OptionsFlowWithReload=_OptionsFlowWithReload)
OLD_HA = SimpleNamespace(OptionsFlow=_OptionsFlow)


def test_current_home_assistant_uses_reloading_options_flow_and_no_listener():
    assert has_reloading_options_flow(NEW_HA)
    assert options_flow_base(NEW_HA) is _OptionsFlowWithReload
    assert needs_update_listener(NEW_HA) is False


def test_old_home_assistant_falls_back_to_listener():
    assert not has_reloading_options_flow(OLD_HA)
    assert options_flow_base(OLD_HA) is _OptionsFlow
    assert needs_update_listener(OLD_HA) is True


def _tree(name):
    with open(os.path.join(PKG, name), encoding="utf-8") as fh:
        return ast.parse(fh.read())


def test_update_listener_only_registered_behind_the_compat_check():
    """Every add_update_listener call in __init__.py sits under needs_update_listener()."""
    tree = _tree("__init__.py")
    guarded = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and "needs_update_listener" in ast.unparse(node.test):
            guarded += sum(
                1 for sub in ast.walk(node)
                if isinstance(sub, ast.Attribute) and sub.attr == "add_update_listener"
            )
    total = sum(
        1 for sub in ast.walk(tree)
        if isinstance(sub, ast.Attribute) and sub.attr == "add_update_listener"
    )
    assert total >= 1 and guarded == total


def test_options_flow_derives_from_the_compat_base():
    tree = _tree("config_flow.py")
    cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "VidaaTVOptionsFlow")
    assert [ast.unparse(b) for b in cls.bases] == ["options_flow_base(config_entries)"]
