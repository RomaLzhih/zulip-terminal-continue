"""
State saved by the application, to carry over into the next run
"""

import configparser
import json
import os
from contextlib import suppress
from typing import Any, Dict, Optional


def state_file_path() -> str:
    """
    The zuliprc file is configuration, which is the user's to write. What the
    application remembers for itself is state, which goes under XDG_STATE_HOME
    (on MacOS too, as with other terminal applications there).
    """
    state_home = os.environ.get("XDG_STATE_HOME", "")
    if not os.path.isabs(state_home):  # Unset, empty, or not valid
        state_home = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(state_home, "zulip-terminal", "state.json")


def load_picked_theme(zuliprc_path: str) -> Optional[str]:
    """
    Returns the theme last picked while running with this zuliprc file, for as
    long as that remains the most recent choice of theme.

    Changing `theme` in the zuliprc file afterwards is a more recent choice, so
    the picked theme is then forgotten, rather than only passed over - or it
    would come back if `theme` was later set to what it used to be.
    """
    state = _read_state()
    zuliprc_key = _zuliprc_key(zuliprc_path)
    saved = state.get(zuliprc_key)
    if not isinstance(saved, dict):
        return None

    if saved.get("zuliprc_theme_when_picked") != _zuliprc_theme(zuliprc_path):
        del state[zuliprc_key]
        with suppress(OSError):
            _write_state(state)
        return None

    picked_theme = saved.get("picked_theme")
    return picked_theme if isinstance(picked_theme, str) else None


def save_picked_theme(zuliprc_path: str, theme_name: str) -> None:
    """
    Remembers a theme picked while running with this zuliprc file, for
    load_picked_theme to start the next run with.

    Raises OSError if it could not be saved.
    """
    state = _read_state()
    state[_zuliprc_key(zuliprc_path)] = {
        "picked_theme": theme_name,
        "zuliprc_theme_when_picked": _zuliprc_theme(zuliprc_path),
    }
    _write_state(state)


def _zuliprc_key(zuliprc_path: str) -> str:
    # State is kept for each zuliprc file, as its settings are
    return os.path.realpath(os.path.expanduser(zuliprc_path))


def _zuliprc_theme(zuliprc_path: str) -> Optional[str]:
    """
    Returns `theme` exactly as set in the zuliprc file, or None if it is not
    """
    zuliprc = configparser.ConfigParser()
    try:
        zuliprc.read(os.path.expanduser(zuliprc_path))
        return zuliprc.get("zterm", "theme", fallback=None)
    except (configparser.Error, UnicodeDecodeError):
        return None


def _read_state() -> Dict[str, Any]:
    try:
        with open(state_file_path()) as state_file:
            state = json.load(state_file)
    except (OSError, ValueError):  # Not saved yet, or unreadable, or not JSON
        return {}
    return state if isinstance(state, dict) else {}


def _write_state(state: Dict[str, Any]) -> None:
    path = state_file_path()
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)

    # Replacing the file in one step ensures another running Zulip Terminal
    # never reads (and then saves back) one which is only partly written
    temporary_path = f"{path}.{os.getpid()}"
    try:
        with open(temporary_path, "w") as state_file:
            json.dump(state, state_file, indent=2, sort_keys=True)
            state_file.write("\n")
        os.replace(temporary_path, path)
    except OSError:
        with suppress(OSError):
            os.remove(temporary_path)
        raise
