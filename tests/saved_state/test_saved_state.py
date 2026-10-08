import json
import os
from pathlib import Path
from typing import Callable, Optional, Union

import pytest
from pytest_mock import MockerFixture

from zulipterminal.saved_state import (
    load_picked_theme,
    save_picked_theme,
    state_file_path,
)


MODULE = "zulipterminal.saved_state"

ZuliprcFactory = Callable[..., str]


@pytest.fixture
def zuliprc(tmp_path: Path) -> ZuliprcFactory:
    """
    Writes (or rewrites) a zuliprc file, setting `theme` in it only if given
    """

    def factory(
        theme: Optional[str] = None,
        *,
        name: str = "zuliprc",
        autohide: str = "no_autohide",
    ) -> str:
        lines = ["[api]", "", "[zterm]", f"autohide={autohide}"]
        if theme is not None:
            lines.append(f"theme={theme}")
        zuliprc_path = tmp_path / name
        zuliprc_path.write_text("\n".join(lines))
        return str(zuliprc_path)

    return factory


def test_state_file_path(state_home: Path) -> None:
    assert state_file_path() == str(state_home / "zulip-terminal" / "state.json")


@pytest.mark.parametrize(
    "xdg_state_home",
    [None, "", "relative/path"],
    ids=["unset", "empty", "not_valid_as_relative"],
)
def test_state_file_path__default_state_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, xdg_state_home: Optional[str]
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    if xdg_state_home is None:
        monkeypatch.delenv("XDG_STATE_HOME")
    else:
        monkeypatch.setenv("XDG_STATE_HOME", xdg_state_home)

    assert state_file_path() == str(
        tmp_path / ".local" / "state" / "zulip-terminal" / "state.json"
    )


def test_load_picked_theme__none_picked(
    zuliprc: ZuliprcFactory, state_home: Path
) -> None:
    assert load_picked_theme(zuliprc("zt_light")) is None

    # Only looking does not leave anything behind
    assert not state_home.exists()


@pytest.mark.parametrize(
    "zuliprc_theme",
    [None, "zt_light", "default"],
    ids=["no_theme_in_zuliprc", "theme_in_zuliprc", "theme_alias_in_zuliprc"],
)
def test_save_picked_theme(
    zuliprc: ZuliprcFactory, zuliprc_theme: Optional[str]
) -> None:
    zuliprc_path = zuliprc(zuliprc_theme)

    save_picked_theme(zuliprc_path, "gruvbox_dark")

    assert load_picked_theme(zuliprc_path) == "gruvbox_dark"
    # ...for every later run too, not only the next one
    assert load_picked_theme(zuliprc_path) == "gruvbox_dark"


def test_save_picked_theme__replaces_previous_pick(zuliprc: ZuliprcFactory) -> None:
    zuliprc_path = zuliprc("zt_light")
    save_picked_theme(zuliprc_path, "gruvbox_dark")

    save_picked_theme(zuliprc_path, "nord")

    assert load_picked_theme(zuliprc_path) == "nord"


def test_save_picked_theme__per_zuliprc(zuliprc: ZuliprcFactory) -> None:
    work_zuliprc = zuliprc("zt_light", name="work_zuliprc")
    home_zuliprc = zuliprc("zt_blue", name="home_zuliprc")
    other_zuliprc = zuliprc("zt_dark", name="other_zuliprc")

    save_picked_theme(work_zuliprc, "gruvbox_dark")
    save_picked_theme(home_zuliprc, "nord")

    assert load_picked_theme(work_zuliprc) == "gruvbox_dark"
    assert load_picked_theme(home_zuliprc) == "nord"
    assert load_picked_theme(other_zuliprc) is None


def test_save_picked_theme__same_zuliprc_by_other_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, zuliprc: ZuliprcFactory
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    zuliprc_path = zuliprc("zt_light")
    link_path = tmp_path / "link_to_zuliprc"
    link_path.symlink_to(zuliprc_path)

    save_picked_theme("~/zuliprc", "gruvbox_dark")

    assert load_picked_theme(zuliprc_path) == "gruvbox_dark"
    assert load_picked_theme(str(link_path)) == "gruvbox_dark"


@pytest.mark.parametrize(
    "theme_when_picked, theme_since",
    [
        ("zt_light", "zt_blue"),
        ("zt_light", None),
        (None, "zt_blue"),
        # Even to the theme which was picked: it is not the picker's any more
        ("zt_light", "gruvbox_dark"),
    ],
    ids=["changed", "removed", "added", "changed_to_picked_theme"],
)
def test_load_picked_theme__zuliprc_theme_changed_since(
    zuliprc: ZuliprcFactory,
    theme_when_picked: Optional[str],
    theme_since: Optional[str],
) -> None:
    zuliprc_path = zuliprc(theme_when_picked)
    save_picked_theme(zuliprc_path, "gruvbox_dark")

    zuliprc(theme_since)

    assert load_picked_theme(zuliprc_path) is None

    # It is forgotten, so does not return if that change is later undone
    zuliprc(theme_when_picked)

    assert load_picked_theme(zuliprc_path) is None


def test_load_picked_theme__zuliprc_theme_changed_since__cannot_forget(
    mocker: MockerFixture, zuliprc: ZuliprcFactory
) -> None:
    zuliprc_path = zuliprc("zt_light")
    save_picked_theme(zuliprc_path, "gruvbox_dark")
    zuliprc("zt_blue")
    mocker.patch(MODULE + ".os.replace", side_effect=OSError("Read-only file system"))

    # Being unable to save anything must not get in the way of starting up
    assert load_picked_theme(zuliprc_path) is None


def test_load_picked_theme__zuliprc_theme_changed_before_picking(
    zuliprc: ZuliprcFactory,
) -> None:
    zuliprc_path = zuliprc("zt_light")
    save_picked_theme(zuliprc_path, "gruvbox_dark")
    zuliprc("zt_blue")

    # The theme is picked last here, even though no run came in between
    save_picked_theme(zuliprc_path, "nord")

    assert load_picked_theme(zuliprc_path) == "nord"


def test_load_picked_theme__other_zuliprc_setting_changed_since(
    zuliprc: ZuliprcFactory,
) -> None:
    zuliprc_path = zuliprc("zt_light")
    save_picked_theme(zuliprc_path, "gruvbox_dark")

    zuliprc("zt_light", autohide="autohide")

    assert load_picked_theme(zuliprc_path) == "gruvbox_dark"


def test_load_picked_theme__forgetting_keeps_other_zuliprcs(
    zuliprc: ZuliprcFactory,
) -> None:
    work_zuliprc = zuliprc("zt_light", name="work_zuliprc")
    home_zuliprc = zuliprc("zt_blue", name="home_zuliprc")
    save_picked_theme(work_zuliprc, "gruvbox_dark")
    save_picked_theme(home_zuliprc, "nord")

    zuliprc("zt_dark", name="work_zuliprc")

    assert load_picked_theme(work_zuliprc) is None
    assert load_picked_theme(home_zuliprc) == "nord"


@pytest.mark.parametrize(
    "zuliprc_content",
    ["theme=zt_light", "[zterm]\ntheme=%(nothing)s", "[zterm]\ntheme=a\ntheme=b"],
    ids=["no_section", "bad_interpolation", "duplicate_option"],
)
def test_save_picked_theme__zuliprc_not_parseable(
    tmp_path: Path, zuliprc_content: str
) -> None:
    zuliprc_path = tmp_path / "zuliprc"
    zuliprc_path.write_text(zuliprc_content)

    # Such a file stops the application from starting, but if it becomes one
    # while running, that must not break switching theme
    save_picked_theme(str(zuliprc_path), "gruvbox_dark")

    assert load_picked_theme(str(zuliprc_path)) == "gruvbox_dark"


@pytest.mark.parametrize(
    "saved",
    [
        "",
        "theme: gruvbox_dark",
        '"gruvbox_dark"',
        '{"ZULIPRC": "gruvbox_dark"}',
        '{"ZULIPRC": {"zuliprc_theme_when_picked": "zt_light"}}',
        '{"ZULIPRC": {"zuliprc_theme_when_picked": "zt_light", "picked_theme": 3}}',
        "\N{SNOWMAN}".encode("utf-16"),
    ],
    ids=[
        "empty",
        "not_json",
        "not_an_object",
        "zuliprc_state_not_an_object",
        "no_picked_theme",
        "picked_theme_not_text",
        "not_text",
    ],
)
def test_load_picked_theme__unusable_saved_state(
    zuliprc: ZuliprcFactory, saved: Union[str, bytes]
) -> None:
    zuliprc_path = zuliprc("zt_light")
    state_file = Path(state_file_path())
    state_file.parent.mkdir(parents=True)
    if isinstance(saved, str):
        # State is saved for a zuliprc file by its real path
        zuliprc_in_json = json.dumps(os.path.realpath(zuliprc_path))
        saved = saved.replace('"ZULIPRC"', zuliprc_in_json).encode()
    state_file.write_bytes(saved)

    assert load_picked_theme(zuliprc_path) is None

    # ...and a theme can still be picked afterwards
    save_picked_theme(zuliprc_path, "gruvbox_dark")

    assert load_picked_theme(zuliprc_path) == "gruvbox_dark"


def test_save_picked_theme__state_home_not_usable(
    zuliprc: ZuliprcFactory, state_home: Path
) -> None:
    state_home.parent.mkdir(parents=True, exist_ok=True)
    state_home.write_text("A file, where the folder for saved state should be")

    with pytest.raises(OSError):
        save_picked_theme(zuliprc("zt_light"), "gruvbox_dark")


def test_save_picked_theme__state_file_not_replaceable(
    zuliprc: ZuliprcFactory,
) -> None:
    state_file = Path(state_file_path())
    state_file.mkdir(parents=True)  # A folder, where the file should be

    with pytest.raises(OSError):
        save_picked_theme(zuliprc("zt_light"), "gruvbox_dark")

    # The file being written, to replace it with, is not left behind
    assert os.listdir(state_file.parent) == ["state.json"]
