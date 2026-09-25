"""Per-machine display preferences (preferences.json).

Holds only display settings (theme, font size, advanced mode). It holds
no PHI, which is why it is the one file in the data folder that is not
encrypted. It is read before login so the login screen uses the chosen
theme. Security settings (idle timeout, retention) are kept inside the
encrypted database, and only an admin can change them.
"""

from __future__ import annotations

import json

from . import config, crypto

THEMES = ("system", "light", "dark")
FONT_SCALES = {"Small": 0.9, "Standard": 1.0, "Large": 1.15, "Extra large": 1.3}
DEFAULTS = {"theme": "system", "font_scale": "Standard", "advanced": False,
            "show_getting_started": True}


def _path():
    return config.data_dir() / "preferences.json"


def load() -> dict:
    prefs = dict(DEFAULTS)
    try:
        data = json.loads(_path().read_text("utf-8"))
        if data.get("theme") in THEMES:
            prefs["theme"] = data["theme"]
        if data.get("font_scale") in FONT_SCALES:
            prefs["font_scale"] = data["font_scale"]
        prefs["advanced"] = bool(data.get("advanced", False))
        prefs["show_getting_started"] = bool(data.get("show_getting_started", True))
    except (OSError, ValueError):
        pass
    return prefs


def save(prefs: dict) -> None:
    clean = {k: prefs.get(k, v) for k, v in DEFAULTS.items()}
    crypto.atomic_write(_path(), json.dumps(clean, indent=2).encode("utf-8"))
