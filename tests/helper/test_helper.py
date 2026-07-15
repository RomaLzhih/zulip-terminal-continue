import base64
import os
from typing import Any, Callable, Dict, Iterable, List, Set, Tuple

import pytest
from pytest import param as case
from pytest_mock import MockerFixture

from zulipterminal.api_types import Composition
from zulipterminal.config.keys import primary_display_key_for_command
from zulipterminal.helper import (
    Index,
    UnreadCounts,
    canonicalize_color,
    classify_unread_counts,
    display_error_if_present,
    download_media,
    get_unused_fence,
    hash_util_decode,
    index_messages,
    kitty_graphics_geometry,
    kitty_graphics_sequence,
    match_group_pm,
    notify_if_message_sent_outside_narrow,
    open_media,
    powerset,
    process_media,
    read_png_dimensions,
    set_count,
    sort_unread_topics,
    terminal_supports_kitty_graphics,
)


MODULE = "zulipterminal.helper"
MODEL = "zulipterminal.model.Model"
SERVER_URL = "https://chat.zulip.org"


def test_index_messages_narrow_all_messages(
    mocker: MockerFixture,
    messages_successful_response: Dict[str, Any],
    index_all_messages: Index,
    initial_index: Index,
) -> None:
    messages = messages_successful_response["messages"]
    model = mocker.patch(MODEL + ".__init__", return_value=None)
    model.index = initial_index
    model.narrow = []
    assert index_messages(messages, model, model.index) == index_all_messages


def test_index_messages_narrow_stream(
    mocker: MockerFixture,
    messages_successful_response: Dict[str, Any],
    index_stream: Index,
    initial_index: Index,
) -> None:
    messages = messages_successful_response["messages"]
    model = mocker.patch(MODEL + ".__init__", return_value=None)
    model.index = initial_index
    model.narrow = [["stream", "PTEST"]]
    model.is_search_narrow.return_value = False
    model.stream_id = 205
    assert index_messages(messages, model, model.index) == index_stream


def test_index_messages_narrow_topic(
    mocker: MockerFixture,
    messages_successful_response: Dict[str, Any],
    index_topic: Index,
    initial_index: Index,
) -> None:
    messages = messages_successful_response["messages"]
    model = mocker.patch(MODEL + ".__init__", return_value=None)
    model.index = initial_index
    model.narrow = [["stream", "7"], ["topic", "Test"]]
    model.is_search_narrow.return_value = False
    model.stream_id = 205
    assert index_messages(messages, model, model.index) == index_topic


def test_index_messages_narrow_user(
    mocker: MockerFixture,
    messages_successful_response: Dict[str, Any],
    index_user: Index,
    initial_index: Index,
) -> None:
    messages = messages_successful_response["messages"]
    model = mocker.patch(MODEL + ".__init__", return_value=None)
    model.index = initial_index
    model.narrow = [["pm-with", "boo@zulip.com"]]
    model.is_search_narrow.return_value = False
    model.user_id = 5140
    model.user_dict = {
        "boo@zulip.com": {
            "user_id": 5179,
        }
    }
    assert index_messages(messages, model, model.index) == index_user


def test_index_messages_narrow_user_multiple(
    mocker: MockerFixture,
    messages_successful_response: Dict[str, Any],
    index_user_multiple: Index,
    initial_index: Index,
) -> None:
    messages = messages_successful_response["messages"]
    model = mocker.patch(MODEL + ".__init__", return_value=None)
    model.index = initial_index
    model.narrow = [["pm-with", "boo@zulip.com, bar@zulip.com"]]
    model.is_search_narrow.return_value = False
    model.user_id = 5140
    model.user_dict = {
        "boo@zulip.com": {
            "user_id": 5179,
        },
        "bar@zulip.com": {"user_id": 5180},
    }
    assert index_messages(messages, model, model.index) == index_user_multiple


@pytest.mark.parametrize(
    "edited_msgs",
    [
        {537286, 537287, 537288},
        {537286},
        {537287},
        {537288},
        {537286, 537287},
        {537286, 537288},
        {537287, 537288},
    ],
)
def test_index_edited_message(
    mocker: MockerFixture,
    messages_successful_response: Dict[str, Any],
    empty_index: Index,
    edited_msgs: Set[int],
    initial_index: Index,
) -> None:
    messages = messages_successful_response["messages"]
    for msg in messages:
        if msg["id"] in edited_msgs:
            msg["edit_history"] = []
    model = mocker.patch(MODEL + ".__init__", return_value=None)
    model.index = initial_index
    model.narrow = []

    expected_index: Dict[str, Any] = dict(
        empty_index, edited_messages=edited_msgs, all_msg_ids={537286, 537287, 537288}
    )
    for msg_id, msg in expected_index["messages"].items():
        if msg_id in edited_msgs:
            msg["edit_history"] = []

    assert index_messages(messages, model, model.index) == expected_index


@pytest.mark.parametrize(
    "msgs_with_stars",
    [
        {537286, 537287, 537288},
        {537286},
        {537287},
        {537288},
        {537286, 537287},
        {537286, 537288},
        {537287, 537288},
    ],
)
def test_index_starred(
    mocker: MockerFixture,
    messages_successful_response: Dict[str, Any],
    empty_index: Index,
    msgs_with_stars: Set[int],
    initial_index: Index,
) -> None:
    messages = messages_successful_response["messages"]
    for msg in messages:
        if msg["id"] in msgs_with_stars and "starred" not in msg["flags"]:
            msg["flags"].append("starred")

    model = mocker.patch(MODEL + ".__init__", return_value=None)
    model.index = initial_index
    model.narrow = [["is", "starred"]]
    model.is_search_narrow.return_value = False
    expected_index: Dict[str, Any] = dict(
        empty_index, private_msg_ids={537287, 537288}, starred_msg_ids=msgs_with_stars
    )
    for msg_id, msg in expected_index["messages"].items():
        if msg_id in msgs_with_stars and "starred" not in msg["flags"]:
            msg["flags"].append("starred")

    assert index_messages(messages, model, model.index) == expected_index


def test_index_mentioned_messages(
    mocker: MockerFixture,
    messages_successful_response: Dict[str, Any],
    empty_index: Index,
    mentioned_messages_combination: Tuple[Set[int], Set[int]],
    initial_index: Index,
) -> None:
    messages = messages_successful_response["messages"]
    mentioned_messages, wildcard_mentioned_messages = mentioned_messages_combination
    for msg in messages:
        if msg["id"] in mentioned_messages and "mentioned" not in msg["flags"]:
            msg["flags"].append("mentioned")
        if (
            msg["id"] in wildcard_mentioned_messages
            and "wildcard_mentioned" not in msg["flags"]
        ):
            msg["flags"].append("wildcard_mentioned")

    model = mocker.patch(MODEL + ".__init__", return_value=None)
    model.index = initial_index
    model.narrow = [["is", "mentioned"]]
    model.is_search_narrow.return_value = False
    expected_index: Dict[str, Any] = dict(
        empty_index,
        private_msg_ids={537287, 537288},
        mentioned_msg_ids=(mentioned_messages | wildcard_mentioned_messages),
    )

    for msg_id, msg in expected_index["messages"].items():
        if msg_id in mentioned_messages and "mentioned" not in msg["flags"]:
            msg["flags"].append("mentioned")
        if (
            msg["id"] in wildcard_mentioned_messages
            and "wildcard_mentioned" not in msg["flags"]
        ):
            msg["flags"].append("wildcard_mentioned")

    assert index_messages(messages, model, model.index) == expected_index


@pytest.mark.parametrize(
    "iterable, map_func, expected_powerset",
    [
        ([], set, [set()]),
        ([1], set, [set(), {1}]),
        ([1, 2], set, [set(), {1}, {2}, {1, 2}]),
        ([1, 2, 3], set, [set(), {1}, {2}, {3}, {1, 2}, {1, 3}, {2, 3}, {1, 2, 3}]),
        ([1, 2], tuple, [(), (1,), (2,), (1, 2)]),
    ],
)
def test_powerset(
    iterable: Iterable[Any],
    map_func: Callable[[Any], Any],
    expected_powerset: List[Any],
) -> None:
    assert powerset(iterable, map_func) == expected_powerset


@pytest.mark.parametrize(
    "unread_topics, expected_value",
    [
        case({}, [], id="no_unread_topics"),
        case(
            {(99, "topic1"): 1},
            [(99, "topic1")],
            id="single_unread_topic",
        ),
        case(
            {(999, "topic3"): 1, (1000, "topic2"): 1, (1, "topic1"): 1},
            [(1000, "topic2"), (1, "topic1"), (999, "topic3")],
            id="multiple_unread_topics",
        ),
        case(
            {
                (999, "topic3"): 1,
                (1000, "topic2"): 1,
                (1000, "topic4"): 3,
                (1, "topic1"): 1,
            },
            [(1000, "topic2"), (1000, "topic4"), (1, "topic1"), (999, "topic3")],
            id="multiple_unread_topics_in_same_stream",
        ),
    ],
)
def test_sort_unread_topics(
    unread_topics: Dict[Tuple[int, str], int],
    expected_value: List[Tuple[int, str]],
    streams: List[Dict[str, Any]],
) -> None:
    stream_list = [stream["id"] for stream in streams]
    assert sort_unread_topics(unread_topics, stream_list) == expected_value


@pytest.mark.parametrize(
    "text, expected",
    [
        ("yih", True),  # start of a first name
        ("yan", True),  # start of another participant's name
        ("Yihan Zhou", True),  # exact full name
        ("yan@", True),  # start of an email
        ("bo", False),  # matches nobody in the conversation
        ("han", False),  # substring, not a prefix
    ],
)
def test_match_group_pm(text: str, expected: bool) -> None:
    conversation = {
        "full_names": ["Yihan Zhou", "Yan Li"],
        "emails": ["yihan@example.com", "yan@example.com"],
    }
    assert match_group_pm(conversation, text) == expected


@pytest.mark.parametrize(
    "muted_streams, muted_topics, vary_in_unreads",
    [
        (
            {99},
            [["Some general stream", "Some general unread topic"]],
            {
                "all_msg": 8,
                "streams": {99: 1},
                "unread_topics": {(99, "Some private unread topic"): 1},
                "all_mentions": 0,
            },
        ),
        (
            {1000},
            [["Secret stream", "Some private unread topic"]],
            {
                "all_msg": 8,
                "streams": {1000: 3},
                "unread_topics": {(1000, "Some general unread topic"): 3},
                "all_mentions": 0,
            },
        ),
        ({1}, [], {"all_mentions": 0}),
    ],
    ids=[
        "mute_private_stream_mute_general_stream_topic",
        "mute_general_stream_mute_private_stream_topic",
        "no_mute_some_other_stream_muted",
    ],
)
def test_classify_unread_counts(
    mocker: MockerFixture,
    initial_data: Dict[str, Any],
    stream_dict: Dict[int, Dict[str, Any]],
    classified_unread_counts: Dict[str, Any],
    muted_topics: List[List[str]],
    muted_streams: Set[int],
    vary_in_unreads: Dict[str, Any],
) -> None:
    model = mocker.Mock()
    model.stream_dict = stream_dict
    model.initial_data = initial_data
    model.is_muted_topic = mocker.Mock(
        side_effect=(
            lambda stream_id, topic: [model.stream_dict[stream_id]["name"], topic]
            in muted_topics
        )
    )
    model.muted_streams = muted_streams
    assert classify_unread_counts(model) == dict(
        classified_unread_counts, **vary_in_unreads
    )


def _controller_for_set_count(mocker: MockerFixture) -> Any:
    controller = mocker.Mock()
    model = controller.model
    model.user_id = 1
    model.muted_streams = set()
    model.is_muted_stream.return_value = False
    model.is_muted_topic.return_value = False
    model.index = {
        "messages": {
            10: {
                "id": 10,
                "type": "stream",
                "stream_id": 205,
                "subject": "Some topic",
                "sender_id": 2,
                "flags": [],
            }
        }
    }
    model.unread_counts = UnreadCounts(
        all_msg=5,  # drifted: per-conversation counts add up to 3
        all_pms=1,
        all_mentions=0,
        unread_topics={(205, "Some topic"): 2},
        unread_pms={2: 1},
        unread_huddles={},
        streams={205: 2},
    )
    controller.view.left_panel.is_in_topic_view = False
    controller.view.stream_w.streams_btn_list = []
    controller.view.user_w.users_btn_list = []
    return controller


def test_set_count_derives_aggregates_from_conversation_counts(
    mocker: MockerFixture,
) -> None:
    # all_msg/all_pms are recomputed from the per-conversation counts on
    # every change, so pre-existing drift in the aggregates (previously
    # adjusted incrementally, persisting until restart) is corrected.
    controller = _controller_for_set_count(mocker)

    set_count([10], controller, -1)

    unread_counts = controller.model.unread_counts
    assert unread_counts["unread_topics"] == {(205, "Some topic"): 1}
    assert unread_counts["all_msg"] == 2  # 1 stream + 1 pm, not 5 - 1
    assert unread_counts["all_pms"] == 1
    controller.view.home_button.update_count.assert_called_once_with(2)
    controller.view.pm_button.update_count.assert_called_once_with(1)


def test_set_count_aggregates_exclude_muted(mocker: MockerFixture) -> None:
    # Muted streams and muted topics stay out of all_msg, as in
    # classify_unread_counts.
    controller = _controller_for_set_count(mocker)
    model = controller.model
    model.muted_streams = {99}
    model.is_muted_topic.side_effect = (
        lambda stream_id, topic: topic == "Muted topic"
    )
    model.unread_counts["unread_topics"].update(
        {(99, "Other topic"): 4, (205, "Muted topic"): 3}
    )

    set_count([10], controller, -1)

    unread_counts = controller.model.unread_counts
    assert unread_counts["all_msg"] == 2  # 1 non-muted stream + 1 pm
    controller.view.home_button.update_count.assert_called_once_with(2)


@pytest.mark.parametrize(
    "color", ["#ffffff", "#f0f0f0", "#f0f1f2", "#fff", "#FFF", "#F3F5FA"]
)
def test_color_formats(mocker: MockerFixture, color: str) -> None:
    canon = canonicalize_color(color)
    assert canon == "#fff"


@pytest.mark.parametrize(
    "color", ["#", "#f", "#ff", "#ffff", "#fffff", "#fffffff", "#abj", "#398a0s"]
)
def test_invalid_color_format(mocker: MockerFixture, color: str) -> None:
    with pytest.raises(ValueError) as e:
        canonicalize_color(color)
    assert str(e.value) == f'Unknown format for color "{color}"'


@pytest.mark.parametrize(
    "response, footer_updated",
    [
        ({"result": "error", "msg": "Request failed."}, True),
        ({"result": "success", "msg": "msg content"}, False),
    ],
)
def test_display_error_if_present(
    mocker: MockerFixture, response: Dict[str, str], footer_updated: bool
) -> None:
    controller = mocker.Mock()
    report_error = controller.report_error

    display_error_if_present(response, controller)

    if footer_updated:
        report_error.assert_called_once_with([response["msg"]])
    else:
        report_error.assert_not_called()


@pytest.mark.parametrize(
    "req, narrow, footer_updated",
    [
        case(
            {"type": "private", "to": [1], "content": "bar"},
            [["is", "private"]],
            False,
            id="all_private__pm__not_notified",
        ),
        case(
            {"type": "private", "to": [4, 5], "content": "Hi"},
            [["pm-with", "welcome-bot@zulip.com, notification-bot@zulip.com"]],
            False,
            id="group_private_conv__same_group_pm__not_notified",
        ),
        case(
            {"type": "private", "to": [4, 5], "content": "Hi"},
            [["pm-with", "welcome-bot@zulip.com"]],
            True,
            id="private_conv__other_pm__notified",
        ),
        case(
            {"type": "private", "to": [4], "content": ":party_parrot:"},
            [
                [
                    "pm-with",
                    "person1@example.com, person2@example.com, "
                    "welcome-bot@zulip.com",
                ]
            ],
            True,
            id="private_conv__other_pm2__notified",
        ),
        case(
            {"type": "stream", "to": "ZT", "subject": "1", "content": "foo"},
            [["stream", "ZT"], ["topic", "1"]],
            False,
            id="stream_topic__same_stream_topic__not_notified",
        ),
        case(
            {"type": "stream", "to": "here", "subject": "pytest", "content": "py"},
            [["stream", "test here"]],
            True,
            id="stream__different_stream__notified",
        ),
        case(
            {
                "type": "stream",
                "to": "|new_stream|",
                "subject": "(no topic)",
                "content": "Hi `|new_stream|`",
            },
            [],
            False,
            id="all_messages__stream__not_notified",
        ),
        case(
            {
                "type": "stream",
                "to": "zulip-terminal",
                "subject": "issue#T781",
                "content": "Added tests",
            },
            [["is", "starred"]],
            True,
            id="starred__stream__notified",
        ),
        case(
            {"type": "private", "to": [1], "content": "fist_bump"},
            [["is", "mentioned"]],
            True,
            id="mentioned__private_no_mention__notified",
        ),
        case(
            {"type": "stream", "to": "PTEST", "subject": "TEST", "content": "Test"},
            [["stream", "PTEST"], ["search", "FOO"]],
            True,
            id="stream_search__stream_match_not_search__notified",
        ),
    ],
)
def test_notify_if_message_sent_outside_narrow(
    mocker: MockerFixture,
    req: Composition,
    narrow: List[Any],
    footer_updated: bool,
    user_id_email_dict: Dict[int, str],
) -> None:
    controller = mocker.Mock()
    report_success = controller.report_success
    controller.model.narrow = narrow
    controller.model.user_id_email_dict = user_id_email_dict

    notify_if_message_sent_outside_narrow(req, controller)

    if footer_updated:
        key = primary_display_key_for_command("NARROW_MESSAGE_RECIPIENT")
        report_success.assert_called_once_with(
            [
                "Message is sent outside of current narrow."
                f" Press [{key}] to narrow to conversation."
            ],
            duration=6,
        )
    else:
        report_success.assert_not_called()


@pytest.mark.parametrize(
    "quoted_string, expected_unquoted_string",
    [
        ("(no.20topic)", "(no topic)"),
        (".3Cstrong.3Exss.3C.2Fstrong.3E", "<strong>xss</strong>"),
        (".23test-here.20.23T1.20.23T2.20.23T3", "#test-here #T1 #T2 #T3"),
        (".2Edot", ".dot"),
        (".3Aparty_parrot.3A", ":party_parrot:"),
    ],
)
def test_hash_util_decode(quoted_string: str, expected_unquoted_string: str) -> None:
    return_value = hash_util_decode(quoted_string)

    assert return_value == expected_unquoted_string


@pytest.mark.parametrize(
    "message_content, expected_fence",
    [
        ("Hi `test_here`", "```"),
        ("```quote\nZ(dot)T(dot)\n```\nempty body", "````"),
        ("```python\ndef zulip():\n  pass\n```\ncode-block", "````"),
        ("````\ndont_know_what_this_does\n````", "`````"),
        ("````quote\n```\ndef zulip():\n  pass\n```\n````", "`````"),
        ("```math\n\\int_a^b f(t)\\, dt = F(b) - F(a)\n```", "````"),
        ("```spoiler Header Text\nSpoiler content\n```", "````"),
    ],
    ids=[
        "inline_code",
        "block_quote",
        "block_code_python",
        "block_code",
        "block_code_quoted",
        "block_math",
        "block_spoiler",
    ],
)
def test_get_unused_fence(message_content: str, expected_fence: str) -> None:
    generated_fence = get_unused_fence(message_content)

    assert generated_fence == expected_fence


def test_download_media(
    mocker: MockerFixture,
    media_path: str = "/tmp/zt-somerandomtext-image.png",
    url: str = SERVER_URL + "/user_uploads/path/image.png",
) -> None:
    mocker.patch(MODULE + ".requests")
    mocker.patch(MODULE + ".open")
    callback = mocker.patch("zulipterminal.ui.View.set_footer_text")
    (
        mocker.patch(
            MODULE + ".NamedTemporaryFile"
        ).return_value.__enter__.return_value.name
    ) = media_path
    controller = mocker.Mock()

    assert media_path == download_media(controller, url, callback)


@pytest.mark.parametrize(
    "platform, download_media_called, show_media_called, tool, modified_media_path",
    [
        ("Linux", True, True, "xdg-open", "/path/to/media"),
        ("MacOS", True, True, "open", "/path/to/media"),
        ("WSL", True, True, "explorer.exe", "\\path\\to\\media"),
        ("UnknownOS", True, False, "unknown-tool", "/path/to/media"),
    ],
    ids=[
        "Linux_os_user",
        "Mac_os_user",
        "WSL_os_user",
        "Unsupported_os_user",
    ],
)
def test_process_media(
    mocker: MockerFixture,
    platform: str,
    download_media_called: bool,
    show_media_called: bool,
    tool: str,
    modified_media_path: str,
    media_path: str = "/path/to/media",
    link: str = "/url/of/media",
) -> None:
    controller = mocker.Mock()
    controller.render_image_in_terminal.return_value = False
    mocked_download_media = mocker.patch(
        MODULE + ".download_media", return_value=media_path
    )
    mocked_open_media = mocker.patch(MODULE + ".open_media")
    mocker.patch(MODULE + ".PLATFORM", platform)
    mocker.patch("zulipterminal.core.Controller.show_media_confirmation_popup")

    process_media(controller, link)

    assert mocked_download_media.called == download_media_called
    assert controller.show_media_confirmation_popup.called == show_media_called
    if show_media_called:
        controller.show_media_confirmation_popup.assert_called_once_with(
            mocked_open_media, tool, modified_media_path
        )


@pytest.mark.parametrize(
    "rendered_in_terminal, show_media_called",
    [
        (True, False),
        (False, True),
    ],
    ids=[
        "image_rendered_in_terminal",
        "no_terminal_renderer_falls_back_to_external_app",
    ],
)
def test_process_media__image_prefers_terminal_render(
    mocker: MockerFixture,
    rendered_in_terminal: bool,
    show_media_called: bool,
    media_path: str = "/path/to/media.png",
    link: str = "/url/of/media.png",
) -> None:
    controller = mocker.Mock()
    controller.render_image_in_terminal.return_value = rendered_in_terminal
    mocker.patch(MODULE + ".download_media", return_value=media_path)
    mocker.patch(MODULE + ".open_media")
    mocker.patch(MODULE + ".PLATFORM", "MacOS")

    process_media(controller, link)

    controller.render_image_in_terminal.assert_called_once_with(media_path)
    assert controller.show_media_confirmation_popup.called == show_media_called


def _make_png(width: int, height: int) -> bytes:
    """Builds a minimal valid PNG of the given size (no image library needed)."""
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return (
            len(data).to_bytes(4, "big")
            + body
            + (zlib.crc32(body) & 0xFFFFFFFF).to_bytes(4, "big")
        )

    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def test_read_png_dimensions__png(tmp_path: Any) -> None:
    path = tmp_path / "img.png"
    path.write_bytes(_make_png(37, 19))

    assert read_png_dimensions(str(path)) == (37, 19)


def test_read_png_dimensions__not_a_png(tmp_path: Any) -> None:
    path = tmp_path / "not.png"
    path.write_bytes(b"this is definitely not a PNG file at all!!")

    assert read_png_dimensions(str(path)) is None


def test_read_png_dimensions__missing_file() -> None:
    assert read_png_dimensions("/no/such/file.png") is None


@pytest.mark.parametrize(
    "env, expected",
    [
        ({"TERM": "xterm-kitty"}, True),
        ({"KITTY_WINDOW_ID": "1"}, True),
        ({"TERM": "xterm-ghostty"}, True),
        ({"TERM_PROGRAM": "ghostty"}, True),
        ({"TERM_PROGRAM": "WezTerm"}, True),
        ({"WEZTERM_PANE": "0"}, True),
        ({"TERM": "xterm-kitty", "TMUX": "/tmp/tmux-x"}, False),
        ({"TERM": "xterm-ghostty", "STY": "1.pts-0"}, False),
        ({"TERM": "xterm-256color"}, False),
        ({}, False),
    ],
    ids=[
        "kitty_term",
        "kitty_window_id",
        "ghostty_term",
        "ghostty_program",
        "wezterm_program",
        "wezterm_pane",
        "kitty_inside_tmux",
        "ghostty_inside_screen",
        "plain_xterm",
        "empty_env",
    ],
)
def test_terminal_supports_kitty_graphics(
    mocker: MockerFixture, env: Dict[str, str], expected: bool
) -> None:
    mocker.patch.dict(MODULE + ".os.environ", env, clear=True)

    assert terminal_supports_kitty_graphics() is expected


@pytest.mark.parametrize(
    "img_w, img_h, term_cols, term_rows, cell, expected",
    [
        # Wide image, constrained by width; cell 10x20 -> 1:2.
        (800, 400, 80, 24, (10, 20), (80, 20)),
        # Tall image, constrained by height (22 usable rows).
        (400, 800, 80, 24, (10, 20), (22, 22)),
        # Small image is not upscaled.
        (20, 20, 80, 24, (10, 20), (2, 1)),
        # No cell pixel info -> assume 1:2 cell aspect.
        (80, 80, 80, 24, (0, 0), (44, 22)),
    ],
    ids=["wide", "tall", "small_no_upscale", "cell_fallback"],
)
def test_kitty_graphics_geometry(
    mocker: MockerFixture,
    img_w: int,
    img_h: int,
    term_cols: int,
    term_rows: int,
    cell: Tuple[int, int],
    expected: Tuple[int, int],
) -> None:
    mocker.patch(
        MODULE + ".os.get_terminal_size",
        return_value=os.terminal_size((term_cols, term_rows)),
    )
    mocker.patch(MODULE + "._terminal_cell_pixel_size", return_value=cell)

    assert kitty_graphics_geometry(img_w, img_h) == expected


def test_kitty_graphics_sequence__single_chunk() -> None:
    png = b"\x89PNG\r\n\x1a\nsmall"

    sequence = kitty_graphics_sequence(png, cols=12, rows=6)

    assert sequence.startswith("\x1b_Ga=T,f=100,t=d,c=12,r=6,m=0;")
    assert sequence.endswith("\x1b\\")
    payload = sequence[len("\x1b_Ga=T,f=100,t=d,c=12,r=6,m=0;") : -2]
    assert base64.standard_b64decode(payload) == png


def test_kitty_graphics_sequence__multiple_chunks() -> None:
    # ~9000 raw bytes base64-encodes to >8192 chars, forcing three 4096 chunks.
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 9000

    sequence = kitty_graphics_sequence(png, cols=4, rows=2)

    # First chunk carries the control keys and m=1 (more chunks follow).
    assert sequence.startswith("\x1b_Ga=T,f=100,t=d,c=4,r=2,m=1;")
    assert sequence.count("\x1b_G") >= 3  # multiple escape chunks
    assert "\x1b_Gm=1;" in sequence  # a middle continuation chunk
    assert "\x1b_Gm=0;" in sequence  # the final chunk
    # Reassembling every chunk's base64 payload recovers the original bytes.
    payload = "".join(
        esc.split(";", 1)[1] for esc in sequence.split("\x1b\\") if esc
    )
    assert base64.standard_b64decode(payload) == png


def test_process_media_empty_url(
    mocker: MockerFixture,
    link: str = "",
) -> None:
    controller = mocker.Mock()
    mocker.patch("zulipterminal.core.Controller.report_error")
    mocked_download_media = mocker.patch(MODULE + ".download_media")
    mocker.patch("zulipterminal.core.Controller.show_media_confirmation_popup")

    process_media(controller, link)

    mocked_download_media.assert_not_called()
    controller.show_media_confirmation_popup.assert_not_called()
    controller.report_error.assert_called_once_with("The media link is empty")


@pytest.mark.parametrize(
    "returncode, error",
    [
        (0, []),
        (
            1,
            [
                " The tool ",
                ("footer_contrast", "xdg-open"),
                " did not run successfully" ". Exited with ",
                ("footer_contrast", "1"),
            ],
        ),
    ],
)
def test_open_media(
    mocker: MockerFixture,
    returncode: int,
    error: List[Any],
    tool: str = "xdg-open",
    media_path: str = "/tmp/zt-somerandomtext-image.png",
) -> None:
    mocked_run = mocker.patch(MODULE + ".subprocess.run")
    mocked_run.return_value.returncode = returncode
    controller = mocker.Mock()

    open_media(controller, tool, media_path)

    assert mocked_run.called
    if error:
        controller.report_error.assert_called_once_with(error)
    else:
        controller.report_error.assert_not_called()


def test_open_media_tool_exception(
    mocker: MockerFixture,
    media_path: str = "/tmp/zt-somerandomtext-image.png",
    tool: str = "unsupported-tool",
    error: List[Any] = [
        " The tool ",
        ("footer_contrast", "unsupported-tool"),
        " could not be found",
    ],
) -> None:
    mocker.patch(MODULE + ".subprocess.run", side_effect=FileNotFoundError())
    controller = mocker.Mock()

    open_media(controller, tool, media_path)

    controller.report_error.assert_called_once_with(error)
