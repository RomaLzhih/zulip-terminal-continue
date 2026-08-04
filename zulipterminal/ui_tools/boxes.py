"""
UI boxes for entering text: WriteBox, MessageSearchBox, PanelSearchBox
"""

import os
import re
import shlex
import shutil
import subprocess
import unicodedata
from collections import Counter
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from time import sleep
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

import urwid
from typing_extensions import Final, Literal
from urwid_readline import ReadlineEdit

from zulipterminal.api_types import Composition, PrivateComposition, StreamComposition
from zulipterminal.config.keys import (
    display_keys_for_command,
    is_command_key,
    primary_display_key_for_command,
    primary_key_for_command,
)
from zulipterminal.config.regexes import (
    REGEX_CLEANED_RECIPIENT,
    REGEX_RECIPIENT_EMAIL,
    REGEX_STREAM_AND_TOPIC_FENCED,
    REGEX_STREAM_AND_TOPIC_FENCED_HALF,
    REGEX_STREAM_AND_TOPIC_UNFENCED,
)
from zulipterminal.config.symbols import (
    COMPOSE_HEADER_BOTTOM,
    COMPOSE_HEADER_TOP,
    INVALID_MARKER,
    MESSAGE_RECIPIENTS_BORDER,
    STREAM_TOPIC_SEPARATOR,
)
from zulipterminal.config.ui_mappings import STREAM_ACCESS_TYPE
from zulipterminal.helper import (
    asynch,
    clipboard_image_to_file,
    format_string,
    match_emoji,
    match_group,
    match_stream,
    match_topics,
    match_user,
    match_user_name_and_email,
)
from zulipterminal.ui_tools.buttons import EditModeButton
from zulipterminal.urwid_types import urwid_Size


# This constant defines the maximum character length of a message
# in the compose box that does not trigger a confirmation popup.
MAX_MESSAGE_LENGTH_CONFIRMATION_POPUP: Final = 15


class _MessageEditState(NamedTuple):
    message_id: int
    old_topic: str


DELIMS_MESSAGE_COMPOSE = "\t\n;"

# Leading characters of a message-body token that trigger live autocomplete
# suggestions in the footer (mentions, streams, emojis) as the user types.
AUTOCOMPLETE_PREFIX_CHARS: Final = ("@", "#", ":")

# Compose-box token which uploads a local file on send; the path runs to the
# end of the line. See WriteBox._expand_attachments and autocomplete_path.
ATTACH_TOKEN_PREFIX: Final = "@attach:"

# One-line reminder of the supported normal-mode commands, shown in the footer.
VIM_NORMAL_MODE_HINT: Final = (
    "  i:insert  esc:exit  h j k l  w b  0 $  gg G  a A o O  x dd dw cc cw D C  u p"
)


class VimEditBox(ReadlineEdit):
    """
    Multiline edit box with a basic modal (vim-like) editing mode.

    Starts in "insert" mode, where it behaves exactly like ReadlineEdit.  The
    enclosing WriteBox switches it to "normal" mode on ESC; normal mode maps a
    basic subset of vim motions and operators onto ReadlineEdit's existing
    editing primitives. Unrecognized keys are swallowed in normal mode so stray
    keystrokes cannot insert text or navigate away from the compose box.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.vim_mode = "insert"
        # First key of a pending two-key sequence ("d" or "g"), else None.
        self._vim_pending: Optional[str] = None

    def enter_insert_mode(self) -> None:
        self.vim_mode = "insert"
        self._vim_pending = None

    def enter_normal_mode(self) -> None:
        self.vim_mode = "normal"
        self._vim_pending = None

    def keypress(self, size: urwid_Size, key: str) -> Optional[str]:
        if self.vim_mode != "normal":
            return super().keypress(size, key)
        # Motions such as next_line/end_of_line rely on self.size, which is
        # normally refreshed by ReadlineEdit.keypress; set it here too.
        self.size = size
        return self._normal_mode_keypress(key)

    def _normal_mode_keypress(self, key: str) -> Optional[str]:
        pending = self._vim_pending
        self._vim_pending = None

        if pending in ("d", "c"):
            # operator-pending: d/c + motion deletes that text; c ("change")
            # then enters insert mode. "dd"/"cc" act on the whole line.
            if key == pending:
                self.kill_whole_line()
            elif key == "w":
                self.kill_word()
            elif key == "b":
                self.backward_kill_word()
            elif key == "$":
                self.forward_kill_line()
            elif key == "0":
                self.backward_kill_line()
            else:
                # Unrecognized motion cancels the operator without editing.
                return None
            if pending == "c":
                self.enter_insert_mode()
            self._invalidate()
            return None
        if pending == "g":
            if key == "g":
                self.set_edit_pos(0)
            self._invalidate()
            return None

        # Motions
        if key in ("h", "left"):
            self.backward_char()
        elif key in ("l", "right"):
            self.forward_char()
        elif key in ("j", "down"):
            self.next_line()
        elif key in ("k", "up"):
            self.previous_line()
        elif key == "w":
            self.forward_word()
        elif key in ("e",):
            self.forward_word()
        elif key == "b":
            self.backward_word()
        elif key in ("0", "^", "home"):
            self.beginning_of_line()
        elif key in ("$", "end"):
            self.end_of_line()
        elif key == "G":
            self.set_edit_pos(len(self.edit_text))
        # Enter insert mode
        elif key == "i":
            self.enter_insert_mode()
        elif key == "a":
            self.forward_char()
            self.enter_insert_mode()
        elif key == "I":
            self.beginning_of_line()
            self.enter_insert_mode()
        elif key == "A":
            self.end_of_line()
            self.enter_insert_mode()
        elif key == "o":
            self.end_of_line()
            self.insert_text("\n")
            self.enter_insert_mode()
        elif key == "O":
            self.beginning_of_line()
            self.insert_text("\n")
            self.backward_char()
            self.enter_insert_mode()
        # Edits
        elif key == "x":
            self.delete_char()
        elif key == "D":
            self.forward_kill_line()
        elif key == "C":
            self.forward_kill_line()
            self.enter_insert_mode()
        elif key == "s":
            self.delete_char()
            self.enter_insert_mode()
        elif key == "u":
            self.undo()
        elif key == "p":
            self.paste()
        # Start of a two-key operator/sequence
        elif key in ("d", "c"):
            self._vim_pending = key
        elif key == "g":
            self._vim_pending = "g"
        # Any other key is swallowed to keep normal mode self-contained.

        self._invalidate()
        return None


class WriteBox(urwid.Pile):
    def __init__(self, view: Any) -> None:
        super().__init__(self.main_view(True))
        self.model = view.model
        self.view = view

        # Used to indicate user's compose status, "closed" by default
        self.compose_box_status: Literal[
            "open_with_private", "open_with_stream", "closed"
        ]

        # If editing a message, its state - otherwise None
        self.msg_edit_state: Optional[_MessageEditState]
        # Determines if the message body (content) can be edited
        self.msg_body_edit_enabled: bool

        self.is_in_typeahead_mode = False
        # Whether the footer currently shows the vim NORMAL-mode indicator.
        self._vim_normal_footer_shown = False

        # Set to int for stream box only
        self.stream_id: Optional[int]

        # Used in PM and stream boxes
        # (empty list implies PM box empty, or not initialized)
        # Prioritizes autocomplete in message body
        self.recipient_user_ids: List[int]

        # Updates server on PM typing events
        # Is separate from recipient_user_ids because we
        # don't include the user's own id in this list
        self.typing_recipient_user_ids: List[int]

        # Private message recipient text entry, None if stream-box
        # or not initialized
        self.to_write_box: Optional[ReadlineEdit]

        # For tracking sending typing status updates
        self.send_next_typing_update: datetime
        self.last_key_update: datetime
        self.idle_status_tracking: bool
        self.sent_start_typing_status: bool

        self._set_compose_attributes_to_defaults()

        # Constant indices into self.contents
        # (CONTAINER=vertical, HEADER/MESSAGE=horizontal)
        self.FOCUS_CONTAINER_HEADER = 0
        self.FOCUS_HEADER_BOX_RECIPIENT = 0
        self.FOCUS_HEADER_BOX_STREAM = 1
        self.FOCUS_HEADER_BOX_TOPIC = 3
        self.FOCUS_HEADER_BOX_EDIT = 4
        self.FOCUS_CONTAINER_MESSAGE = 1
        self.FOCUS_MESSAGE_BOX_BODY = 0
        # These are included to allow improved clarity
        # FIXME: These elements don't acquire focus; replace prefix & in above?
        self.FOCUS_HEADER_PREFIX_STREAM = 0
        self.FOCUS_HEADER_PREFIX_TOPIC = 2

    def _set_compose_attributes_to_defaults(self) -> None:
        self.compose_box_status = "closed"

        self.msg_edit_state = None
        self.msg_body_edit_enabled = True

        self.stream_id = None
        self.to_write_box = None

        # Maintain synchrony between *_user_ids by setting them
        # to empty lists together using the helper method.
        self._set_regular_and_typing_recipient_user_ids(None)

        self.send_next_typing_update = datetime.now()
        self.last_key_update = datetime.now()
        self.idle_status_tracking = False
        self.sent_start_typing_status = False

        if hasattr(self, "msg_write_box"):
            self.msg_write_box.edit_text = ""

    def main_view(self, new: bool) -> Any:
        if new:
            return []
        else:
            self.contents.clear()

    def set_editor_mode(self) -> None:
        self.view.controller.enter_editor_mode_with(self)

    def _set_regular_and_typing_recipient_user_ids(
        self, user_id_list: Optional[List[int]]
    ) -> None:
        if user_id_list:
            self.recipient_user_ids = user_id_list
            self.typing_recipient_user_ids = [
                user_id
                for user_id in self.recipient_user_ids
                if user_id != self.model.user_id
            ]
        else:
            self.recipient_user_ids = list()
            self.typing_recipient_user_ids = list()

    def send_stop_typing_status(self) -> None:
        # Send 'stop' updates only for PM narrows, when there are recipients
        # to send to and a prior 'start' status has already been sent.
        if (
            self.compose_box_status == "open_with_private"
            and self.typing_recipient_user_ids
            and self.sent_start_typing_status
        ):
            self.model.send_typing_status_by_user_ids(
                self.typing_recipient_user_ids, status="stop"
            )
            self.send_next_typing_update = datetime.now()
            self.idle_status_tracking = False
            self.sent_start_typing_status = False

    def private_box_view(
        self,
        *,
        recipient_user_ids: Optional[List[int]] = None,
    ) -> None:
        self.set_editor_mode()

        self.compose_box_status = "open_with_private"

        if recipient_user_ids:
            self._set_regular_and_typing_recipient_user_ids(recipient_user_ids)
            self.recipient_emails = [
                self.model.user_id_email_dict[user_id]
                for user_id in self.recipient_user_ids
            ]
            recipient_info = ", ".join(
                [
                    f"{self.model.user_dict[email]['full_name']} <{email}>"
                    for email in self.recipient_emails
                ]
            )
        else:
            self._set_regular_and_typing_recipient_user_ids(None)
            self.recipient_emails = []
            recipient_info = ""

        self.send_next_typing_update = datetime.now()
        self.to_write_box = ReadlineEdit("To: ", edit_text=recipient_info)
        self.to_write_box.enable_autocomplete(
            func=self._to_box_autocomplete,
            key=primary_key_for_command("AUTOCOMPLETE"),
            key_reverse=primary_key_for_command("AUTOCOMPLETE_REVERSE"),
        )
        self.to_write_box.set_completer_delims("")

        self.msg_write_box = VimEditBox(
            multiline=True, max_char=self.model.max_message_length
        )
        self.msg_write_box.enable_autocomplete(
            func=self.generic_autocomplete,
            key=primary_key_for_command("AUTOCOMPLETE"),
            key_reverse=primary_key_for_command("AUTOCOMPLETE_REVERSE"),
        )
        self.msg_write_box.set_completer_delims(DELIMS_MESSAGE_COMPOSE)

        self.header_write_box = urwid.Columns([self.to_write_box])
        header_line_box = urwid.Pile(
            [
                urwid.Divider(COMPOSE_HEADER_TOP),
                self.header_write_box,
                urwid.Divider(COMPOSE_HEADER_BOTTOM),
            ]
        )
        self.contents = [
            (header_line_box, self.options()),
            (self.msg_write_box, self.options()),
        ]
        self.focus_position = self.FOCUS_CONTAINER_MESSAGE

        start_period_delta = timedelta(
            milliseconds=self.model.typing_started_wait_period
        )
        stop_period_delta = timedelta(
            milliseconds=self.model.typing_stopped_wait_period
        )

        def on_type_send_status(edit: object, new_edit_text: str) -> None:
            if new_edit_text and self.typing_recipient_user_ids:
                self.last_key_update = datetime.now()
                if self.last_key_update > self.send_next_typing_update:
                    self.model.send_typing_status_by_user_ids(
                        self.typing_recipient_user_ids, status="start"
                    )
                    self.send_next_typing_update += start_period_delta
                    self.sent_start_typing_status = True
                    # Initiate tracker function only if it isn't already
                    # initiated.
                    if not self.idle_status_tracking:
                        self.idle_status_tracking = True
                        track_idleness_and_update_status()

        @asynch
        def track_idleness_and_update_status() -> None:
            while datetime.now() < self.last_key_update + stop_period_delta:
                idle_check_time = (
                    self.last_key_update + stop_period_delta - datetime.now()
                )
                sleep(idle_check_time.total_seconds())
            self.send_stop_typing_status()

        urwid.connect_signal(self.msg_write_box, "change", on_type_send_status)

    def update_recipients(self, write_box: ReadlineEdit) -> None:
        self.recipient_emails = re.findall(REGEX_RECIPIENT_EMAIL, write_box.edit_text)
        self._set_regular_and_typing_recipient_user_ids(
            [self.model.user_dict[email]["user_id"] for email in self.recipient_emails]
        )

    def _tidy_valid_recipients_and_notify_invalid_ones(
        self, write_box: ReadlineEdit
    ) -> bool:
        tidied_recipients = list()
        invalid_recipients = list()

        recipients = [
            recipient.strip()
            for recipient in write_box.edit_text.split(",")
            if recipient.strip()  # This condition avoids whitespace recipients (",  ,")
        ]

        for recipient in recipients:
            cleaned_recipient_list = re.findall(REGEX_CLEANED_RECIPIENT, recipient)
            recipient_name, recipient_email, invalid_text = cleaned_recipient_list[0]
            # Discard invalid_text as part of tidying up the recipient.

            if recipient_email and self.model.is_valid_private_recipient(
                recipient_email, recipient_name
            ):
                tidied_recipients.append(f"{recipient_name} <{recipient_email}>")
            else:
                invalid_recipients.append(recipient)
                tidied_recipients.append(recipient)

        write_box.edit_text = ", ".join(tidied_recipients)
        write_box.edit_pos = len(write_box.edit_text)

        if invalid_recipients:
            invalid_recipients_error = [
                "Invalid recipient(s) - " + ", ".join(invalid_recipients),
                " - Use ",
                ("footer_contrast", primary_display_key_for_command("AUTOCOMPLETE")),
                " or ",
                (
                    "footer_contrast",
                    primary_display_key_for_command("AUTOCOMPLETE_REVERSE"),
                ),
                " to autocomplete.",
            ]
            self.view.controller.report_error(invalid_recipients_error)
            return False

        return True

    def _setup_common_stream_compose(
        self, stream_id: int, caption: str, title: str
    ) -> None:
        self.set_editor_mode()
        self.compose_box_status = "open_with_stream"
        self.stream_id = stream_id
        self.recipient_user_ids = self.model.get_other_subscribers_in_stream(
            stream_id=stream_id
        )
        self.msg_write_box = VimEditBox(
            multiline=True, max_char=self.model.max_message_length
        )
        self.msg_write_box.enable_autocomplete(
            func=self.generic_autocomplete,
            key=primary_key_for_command("AUTOCOMPLETE"),
            key_reverse=primary_key_for_command("AUTOCOMPLETE_REVERSE"),
        )
        self.msg_write_box.set_completer_delims(DELIMS_MESSAGE_COMPOSE)

        self.title_write_box = ReadlineEdit(
            edit_text=title, max_char=self.model.max_topic_length
        )
        self.title_write_box.enable_autocomplete(
            func=self._topic_box_autocomplete,
            key=primary_key_for_command("AUTOCOMPLETE"),
            key_reverse=primary_key_for_command("AUTOCOMPLETE_REVERSE"),
        )
        self.title_write_box.set_completer_delims("")

        # NOTE: stream marker should be set during initialization
        self.header_write_box = urwid.Columns(
            [
                ("pack", urwid.Text(("default", "?"))),
                self.stream_write_box,
                ("pack", urwid.Text(STREAM_TOPIC_SEPARATOR)),
                self.title_write_box,
            ],
            dividechars=1,
        )
        header_line_box = urwid.Pile(
            [
                urwid.Divider(COMPOSE_HEADER_TOP),
                self.header_write_box,
                urwid.Divider(COMPOSE_HEADER_BOTTOM),
            ]
        )
        write_box = [
            (header_line_box, self.options()),
            (self.msg_write_box, self.options()),
        ]
        self.contents = write_box

    def stream_box_view(
        self, stream_id: int, caption: str = "", title: str = ""
    ) -> None:
        self.stream_write_box = ReadlineEdit(
            edit_text=caption, max_char=self.model.max_stream_name_length
        )
        self.stream_write_box.enable_autocomplete(
            func=self._stream_box_autocomplete,
            key=primary_key_for_command("AUTOCOMPLETE"),
            key_reverse=primary_key_for_command("AUTOCOMPLETE_REVERSE"),
        )
        self.stream_write_box.set_completer_delims("")
        self._setup_common_stream_compose(stream_id, caption, title)

        # Use and set a callback to set the stream marker
        self._set_stream_write_box_style(None, caption)
        urwid.connect_signal(
            self.stream_write_box, "change", self._set_stream_write_box_style
        )

    def stream_box_edit_view(
        self, stream_id: int, caption: str = "", title: str = ""
    ) -> None:
        self.stream_write_box = urwid.Text(caption)
        self._setup_common_stream_compose(stream_id, caption, title)

        self.edit_mode_button = EditModeButton(
            controller=self.model.controller,
            width=20,
        )
        self.header_write_box.widget_list.append(self.edit_mode_button)

        # Use callback to set stream marker - it shouldn't change, so don't need signal
        self._set_stream_write_box_style(None, caption)

    def _set_stream_write_box_style(self, widget: ReadlineEdit, new_text: str) -> None:
        # FIXME: Refactor when we have ~ Model.is_private_stream
        stream_marker = INVALID_MARKER
        color = "general_bar"
        if self.model.is_valid_stream(new_text):
            stream_id = self.model.stream_id_from_name(new_text)
            stream_access_type = self.model.stream_access_type(stream_id)
            stream_marker = STREAM_ACCESS_TYPE[stream_access_type]["icon"]
            stream = self.model.stream_dict[stream_id]
            color = stream["color"]
        self.header_write_box[self.FOCUS_HEADER_PREFIX_STREAM].set_text(
            (color, stream_marker)
        )

    def _to_box_autocomplete(self, text: str, state: Optional[int]) -> Optional[str]:
        users_list = self.view.users
        recipients = text.rsplit(",", 1)

        # Use the most recent recipient for autocomplete.
        previous_recipients = f"{recipients[0]}, " if len(recipients) > 1 else ""
        latest_text = recipients[-1].strip()

        matching_users = [
            user for user in users_list if match_user_name_and_email(user, latest_text)
        ]

        # Append the potential autocompleted recipients to the string
        # containing the previous recipients.
        updated_recipients = [
            f"{previous_recipients}{user['full_name']} <{user['email']}>"
            for user in matching_users
        ]

        user_names = [user["full_name"] for user in matching_users]

        return self._process_typeaheads(updated_recipients, state, user_names)

    def _topic_box_autocomplete(self, text: str, state: Optional[int]) -> Optional[str]:
        topic_names = self.model.topics_in_stream(self.stream_id)

        topic_typeaheads = match_topics(topic_names, text)

        # Typeaheads and suggestions are the same.
        return self._process_typeaheads(topic_typeaheads, state, topic_typeaheads)

    def _stream_box_autocomplete(
        self, text: str, state: Optional[int]
    ) -> Optional[str]:
        streams_list = self.view.pinned_streams + self.view.unpinned_streams
        streams = [stream["name"] for stream in streams_list]

        # match_streams takes stream names and typeaheads,
        # but we don't have typeaheads here.
        # FIXME: Refactor match_stream
        stream_data = list(zip(streams, streams))
        matched_streams = match_stream(stream_data, text, self.view.pinned_streams)

        # matched_streams[0] and matched_streams[1] contains the same data.
        return self._process_typeaheads(matched_streams[0], state, matched_streams[1])

    def generic_autocomplete(self, text: str, state: Optional[int]) -> Optional[str]:
        # '@attach:' is handled ahead of the prefix map below: it contains both
        # '@' and ':', and the map picks the right-most prefix, so the ':' would
        # otherwise win and offer emojis for what is a path.
        attach_index = text.rfind(ATTACH_TOKEN_PREFIX)
        if attach_index > -1:
            typeaheads, suggestions = self.autocomplete_path(
                text[attach_index:], ATTACH_TOKEN_PREFIX
            )
            typeahead = self._process_typeaheads(typeaheads, state, suggestions)
            if typeahead:
                typeahead = text[:attach_index] + typeahead
            return typeahead

        autocomplete_map = {
            "@_": self.autocomplete_users,
            "@_**": self.autocomplete_users,
            "@": self.autocomplete_mentions,
            "@*": self.autocomplete_groups,
            "@**": self.autocomplete_users,
            "#": self.autocomplete_streams,
            "#**": self.autocomplete_streams,
            ":": self.autocomplete_emojis,
        }

        # Look in a reverse order to find the last autocomplete prefix used in
        # the text. For instance, if text='@#example', use '#' as the prefix.
        # FIXME: Mentions can actually start with '#', and streams with
        #        anything; this implementation simply chooses the right-most
        #        match of the longest length
        prefix_indices = {prefix: text.rfind(prefix) for prefix in autocomplete_map}

        text = self.validate_and_patch_autocomplete_stream_and_topic(
            text, autocomplete_map, prefix_indices
        )

        found_prefix_indices = {
            prefix: index for prefix, index in prefix_indices.items() if index > -1
        }
        # Return text if it doesn't have any of the autocomplete prefixes.
        if not found_prefix_indices:
            return text

        # Use latest longest matching prefix (so @_ wins vs @)
        prefix_index = max(found_prefix_indices.values())
        prefix = max(
            (len(prefix), prefix)
            for prefix, index in found_prefix_indices.items()
            if index == prefix_index
        )[1]
        autocomplete_func = autocomplete_map[prefix]

        # NOTE: The following block only executes if any of the autocomplete
        # prefixes exist.
        typeaheads, suggestions = autocomplete_func(text[prefix_index:], prefix)

        typeahead = self._process_typeaheads(typeaheads, state, suggestions)
        if typeahead:
            typeahead = text[:prefix_index] + typeahead
        return typeahead

    def _process_typeaheads(
        self, typeaheads: List[str], state: Optional[int], suggestions: List[str]
    ) -> Optional[str]:
        num_suggestions = 10
        fewer_typeaheads = typeaheads[:num_suggestions]
        reduced_suggestions = suggestions[:num_suggestions]
        is_truncated = len(fewer_typeaheads) != len(typeaheads)

        if (
            state is not None
            and state < len(fewer_typeaheads)
            and state >= -len(fewer_typeaheads)
        ):
            typeahead: Optional[str] = fewer_typeaheads[state]
        else:
            typeahead = None
            state = None
        self.is_in_typeahead_mode = True
        self.view.set_typeahead_footer(reduced_suggestions, state, is_truncated)
        return typeahead

    def autocomplete_path(
        self, text: str, prefix_string: str
    ) -> Tuple[List[str], List[str]]:
        """
        Complete the filesystem path of an '@attach:<path>' token, shell-style.

        The typed path is split at its last '/' into a directory to list and a
        partial name to match against, case-insensitively. Directories complete
        with a trailing '/' so the next completion descends into them, and
        dotfiles are offered only once the partial name itself starts with '.'.
        A bare '~' completes to '~/'; the directory is otherwise left exactly as
        typed (so '~' is not expanded away), matching _expand_attachments, which
        expands '~' and resolves relative paths against the working directory.
        """
        path = text[len(prefix_string) :]
        if path == "~":
            return [prefix_string + "~/"], ["~/"]

        separator_index = path.rfind(os.sep)
        # The directory as typed, keeping its trailing separator; empty for a
        # bare name, which lists the working directory.
        typed_directory = path[: separator_index + 1]
        partial_name = path[separator_index + 1 :]

        try:
            entries = os.listdir(os.path.expanduser(typed_directory) or ".")
        except OSError:
            # Nonexistent or unreadable directory: nothing to suggest.
            return [], []

        matching_entries = [
            entry
            for entry in entries
            if entry.lower().startswith(partial_name.lower())
            and (partial_name.startswith(".") or not entry.startswith("."))
        ]
        matching_entries.sort(key=str.lower)

        typeaheads = []
        suggestions = []
        for entry in matching_entries:
            full_path = os.path.join(os.path.expanduser(typed_directory), entry)
            name = entry + os.sep if os.path.isdir(full_path) else entry
            typeaheads.append(prefix_string + typed_directory + name)
            suggestions.append(name)
        return typeaheads, suggestions

    def autocomplete_mentions(
        self, text: str, prefix_string: str
    ) -> Tuple[List[str], List[str]]:
        # Handles user mentions (@ mentions and silent mentions)
        # and group mentions.

        user_typeahead, user_names = self.autocomplete_users(text, prefix_string)
        group_typeahead, groups = self.autocomplete_groups(text, prefix_string)

        combined_typeahead = user_typeahead + group_typeahead
        combined_names = user_names + groups

        return combined_typeahead, combined_names

    def autocomplete_users(
        self, text: str, prefix_string: str
    ) -> Tuple[List[str], List[str]]:
        users_list = self.view.users
        matching_users = [
            user for user in users_list if match_user(user, text[len(prefix_string) :])
        ]
        matching_ids = {user["user_id"] for user in matching_users}
        matching_recipient_ids = set(self.recipient_user_ids) & set(matching_ids)
        # When composing to a stream, only suggest its subscribers: mentioning
        # someone who is not in the channel does not notify them, so hide them.
        # (recipient_user_ids holds the stream's other subscribers here.)
        if self.compose_box_status == "open_with_stream":
            matching_users = [
                user
                for user in matching_users
                if user["user_id"] in matching_recipient_ids
            ]
        # Display subscribed users/recipients first.
        sorted_matching_users = sorted(
            matching_users,
            key=lambda user: user["user_id"] in matching_recipient_ids,
            reverse=True,
        )

        user_names = [user["full_name"] for user in sorted_matching_users]

        # Counter holds a count of each name in the list of users' names in a
        # dict-like manner, which is a more efficient approach when compared to
        # slicing the original list on each name.
        # FIXME: Use a persistent counter rather than generate one on each autocomplete.
        user_names_counter = Counter(user_names)

        # Append user_id's to users with the same names.
        user_names_with_distinct_duplicates = [
            f"{user['full_name']}|{user['user_id']}"
            if user_names_counter[user["full_name"]] > 1
            else user["full_name"]
            for user in sorted_matching_users
        ]

        extra_prefix = "{}{}".format(
            "*" if prefix_string[-1] != "*" else "",
            "*" if prefix_string[-2:] != "**" else "",
        )
        user_typeahead = format_string(
            user_names_with_distinct_duplicates, prefix_string + extra_prefix + "{}**"
        )

        return user_typeahead, user_names

    def autocomplete_groups(
        self, text: str, prefix_string: str
    ) -> Tuple[List[str], List[str]]:
        prefix_length = len(prefix_string)
        groups = [
            group_name
            for group_name in self.model.user_group_names
            if match_group(group_name, text[prefix_length:])
        ]

        extra_prefix = "*" if prefix_string[-1] != "*" else ""
        group_typeahead = format_string(groups, prefix_string + extra_prefix + "{}*")
        return group_typeahead, groups

    def autocomplete_streams(
        self, text: str, prefix_string: str
    ) -> Tuple[List[str], List[str]]:
        streams_list = self.view.pinned_streams + self.view.unpinned_streams
        streams = [stream["name"] for stream in streams_list]
        stream_typeahead = format_string(streams, "#**{}**")
        stream_data = list(zip(stream_typeahead, streams))

        prefix_length = len(prefix_string)

        _, matched_streams = match_stream(
            stream_data, text[prefix_length:], self.view.pinned_streams
        )

        muted_streams = [
            self.model.stream_dict[stream_id]["name"]
            for stream_id in self.model.muted_streams
        ]
        matching_muted_streams = [
            stream_name
            for stream_name in matched_streams
            if stream_name in muted_streams
        ]
        pinned_streams = [stream["name"] for stream in self.view.pinned_streams]
        pinned_unpinned_separator = len(set(pinned_streams) & set(matched_streams))
        for matching_muted_stream in matching_muted_streams:
            matched_streams.remove(matching_muted_stream)
            if matching_muted_stream in pinned_streams:
                matched_streams.insert(
                    pinned_unpinned_separator - 1, matching_muted_stream
                )
            else:
                matched_streams.append(matching_muted_stream)

        current_stream = self.model.stream_dict.get(self.stream_id, None)
        if current_stream is not None:
            current_stream_name = current_stream["name"]
            if current_stream_name in matched_streams:
                matched_streams.remove(current_stream_name)
                matched_streams.insert(0, current_stream_name)

        matched_stream_typeaheads = format_string(matched_streams, "#**{}**")
        return matched_stream_typeaheads, matched_streams

    def autocomplete_stream_and_topic(
        self, text: str, prefix_string: str
    ) -> Tuple[List[str], List[str]]:
        match = re.search(REGEX_STREAM_AND_TOPIC_FENCED_HALF, text)

        stream = match.group(1) if match else ""

        if self.model.is_valid_stream(stream):
            stream_id = self.model.stream_id_from_name(stream)
            topic_names = self.model.topics_in_stream(stream_id)
        else:
            topic_names = []

        topic_suggestions = match_topics(topic_names, text[len(prefix_string) :])

        topic_typeaheads = format_string(topic_suggestions, prefix_string + "{}**")

        return topic_typeaheads, topic_suggestions

    def validate_and_patch_autocomplete_stream_and_topic(
        self,
        text: str,
        autocomplete_map: Dict[str, Callable[..., Any]],
        prefix_indices: Dict[str, int],
    ) -> str:
        """
        Checks if a prefix string is possible candidate for stream+topic autocomplete.
        If the prefix matches, we update the autocomplete_map and prefix_indices,
        and return the (updated) text.
        """
        match = re.search(REGEX_STREAM_AND_TOPIC_FENCED_HALF, text)
        match_fenced = re.search(REGEX_STREAM_AND_TOPIC_FENCED, text)
        match_unfenced = re.search(REGEX_STREAM_AND_TOPIC_UNFENCED, text)
        if match:
            prefix = f"#**{match.group(1)}>"
            prefix_indices[prefix] = match.start()
        elif match_fenced:
            # Amending the prefix to remove stream fence `**`
            prefix = f"#**{match_fenced.group(1)}>"
            prefix_with_topic = prefix + match_fenced.group(2)
            prefix_indices[prefix] = match_fenced.start()
            # Amending the text to have new prefix (without `**` fence)
            text = text[: match_fenced.start()] + prefix_with_topic
        elif match_unfenced:
            prefix = f"#**{match_unfenced.group(1)}>"
            prefix_with_topic = prefix + match_unfenced.group(2)
            prefix_indices[prefix] = match_unfenced.start()
            # Amending the text to have new prefix (with `**` fence)
            text = text[: match_unfenced.start()] + prefix_with_topic
        if match or match_fenced or match_unfenced:
            autocomplete_map.update({prefix: self.autocomplete_stream_and_topic})

        return text

    def autocomplete_emojis(
        self, text: str, prefix_string: str
    ) -> Tuple[List[str], List[str]]:
        emoji_list = self.model.all_emoji_names
        emojis = [emoji for emoji in emoji_list if match_emoji(emoji, text[1:])]
        emoji_typeahead = format_string(emojis, ":{}:")

        return emoji_typeahead, emojis

    def request_exit_compose(self) -> None:
        """
        Close the compose box, confirming first if a long message would
        otherwise be lost.

        Shared by EXIT_COMPOSE and by QUIT (ctrl c), which cancels an open
        compose box rather than quitting the application.
        """
        saved_draft = self.model.session_draft_message()
        self.send_stop_typing_status()

        compose_not_in_edit_mode = self.msg_edit_state is None
        compose_box_content = self.msg_write_box.edit_text
        saved_draft_content = saved_draft.get("content") if saved_draft else None

        exceeds_max_length = (
            len(compose_box_content) >= MAX_MESSAGE_LENGTH_CONFIRMATION_POPUP
        )
        not_saved_as_draft = (
            saved_draft is None or compose_box_content != saved_draft_content
        )

        if compose_not_in_edit_mode and exceeds_max_length and not_saved_as_draft:
            self.view.controller.exit_compose_confirmation_popup()
        else:
            self.exit_compose_box()

    def exit_compose_box(self) -> None:
        self._set_default_footer_after_autocomplete()
        self._set_compose_attributes_to_defaults()
        self.view.controller.exit_editor_mode()
        self.main_view(False)
        self.view.middle_column.set_focus("body")

    def _set_default_footer_after_autocomplete(self) -> None:
        self.is_in_typeahead_mode = False
        self.view.set_footer_text()

    def _refresh_autocomplete_footer_preview(self) -> None:
        """
        Show autocomplete candidates in the footer as the user types a mention,
        stream, emoji or '@attach:' path token in the message body, without
        waiting for the AUTOCOMPLETE key. The token is the whitespace-delimited
        word ending at the cursor; if it opens with a recognized prefix we let
        generic_autocomplete populate the footer with state=None, which lists
        the matches without selecting one (a preview). Pressing AUTOCOMPLETE
        then cycles through and inserts them as before.
        """
        if not self.msg_body_edit_enabled:
            return
        text_before_caret = self.msg_write_box.edit_text[: self.msg_write_box.edit_pos]
        # An '@attach:' path runs to the end of the line and may contain
        # spaces, so preview from the token rather than the last word.
        line = text_before_caret.rsplit("\n", 1)[-1]
        attach_index = line.rfind(ATTACH_TOKEN_PREFIX)
        if attach_index > -1:
            self.generic_autocomplete(line[attach_index:], None)
            return
        token = re.split(r"\s", text_before_caret)[-1]
        if token[:1] in AUTOCOMPLETE_PREFIX_CHARS:
            self.generic_autocomplete(token, None)
        elif self.is_in_typeahead_mode:
            self._set_default_footer_after_autocomplete()

    def _msg_box_focused(self) -> bool:
        """Whether the message body box is the currently focused compose box."""
        return (
            self.msg_body_edit_enabled
            and len(self.contents) > 0
            and self.focus_position == self.FOCUS_CONTAINER_MESSAGE
        )

    def _set_vim_normal_mode_footer(self) -> None:
        self.is_in_typeahead_mode = False
        self._vim_normal_footer_shown = True
        self.view.set_footer_text(
            [("footer_contrast", " NORMAL "), VIM_NORMAL_MODE_HINT]
        )

    def _update_message_body_footer(self, is_autocomplete_key: bool) -> None:
        """
        Keep the footer in sync with the message body after a keypress: show the
        vim NORMAL-mode indicator in normal mode, otherwise the live autocomplete
        preview. Skipped for the AUTOCOMPLETE keys, which set the footer (with a
        selection) themselves.
        """
        if is_autocomplete_key or not self._msg_box_focused():
            return
        if self.msg_write_box.vim_mode == "normal":
            if not self._vim_normal_footer_shown:
                self._set_vim_normal_mode_footer()
        else:
            if self._vim_normal_footer_shown:
                self._vim_normal_footer_shown = False
                self._set_default_footer_after_autocomplete()
            self._refresh_autocomplete_footer_preview()

    def _paste_clipboard_image(self) -> None:
        """
        Write the clipboard's image to a temporary file and insert an
        '@attach:<path>' token for it at the cursor, which uploads on send.
        """
        try:
            image_path = clipboard_image_to_file()
        except ValueError as e:
            self.view.controller.report_error([f"Paste failed: {e}"])
            return

        text = self.msg_write_box.edit_text
        cursor = self.msg_write_box.edit_pos
        before, after = text[:cursor], text[cursor:]
        # The token runs to the end of its line, so keep it on a line of its
        # own rather than swallowing whatever the message already says.
        token = f"{ATTACH_TOKEN_PREFIX}{image_path}\n"
        if before and not before.endswith("\n"):
            token = "\n" + token
        self.msg_write_box.edit_text = before + token + after
        self.msg_write_box.edit_pos = len(before) + len(token)
        self.view.controller.report_success(
            [" Image pasted; it uploads when you send the message"]
        )

    def _expand_attachments(self, content: str) -> Optional[str]:
        """
        Upload files referenced by '@attach:<path>' tokens (path runs to the
        end of the line) and replace each token with a markdown link to the
        upload. Returns None if any upload fails, aborting the send.
        """
        def upload(match: Any) -> str:
            path = os.path.expanduser(match.group(1).strip())
            with open(path, "rb") as fp:
                response = self.model.client.upload_file(fp)
            if response.get("result") != "success":
                raise ValueError(response.get("msg", "upload failed"))
            link = response.get("url") or response.get("uri")
            if not link:
                raise ValueError("no URL in upload response")
            return f"[{os.path.basename(path)}]({link})"

        try:
            return re.sub(re.escape(ATTACH_TOKEN_PREFIX) + r"(.+)", upload, content)
        except (OSError, ValueError) as e:
            self.view.controller.report_error([f"Attachment failed: {e}"])
            return None

    def keypress(self, size: urwid_Size, key: str) -> Optional[str]:
        is_autocomplete_key = is_command_key("AUTOCOMPLETE", key) or is_command_key(
            "AUTOCOMPLETE_REVERSE", key
        )
        if self.is_in_typeahead_mode and not is_autocomplete_key:
            # As is, this exits autocomplete even if the user chooses to resume compose.
            # Including a check for "EXIT_COMPOSE" in the above logic would avoid
            # resetting the footer until actually exiting compose, but autocomplete
            # itself does not continue on resume with such a solution.
            # TODO: Fully implement resuming of autocomplete upon resuming compose.
            self._set_default_footer_after_autocomplete()

        # Vim mode: ESC in the message body switches insert -> normal rather than
        # exiting compose; only exit once already in normal mode (or when a header
        # box is focused, handled by the EXIT_COMPOSE branch below).
        if (
            is_command_key("EXIT_COMPOSE", key)
            and self._msg_box_focused()
            and self.msg_write_box.vim_mode == "insert"
        ):
            self.msg_write_box.enter_normal_mode()
            self._set_vim_normal_mode_footer()
            return None

        if is_command_key("PASTE_IMAGE", key) and self.msg_body_edit_enabled:
            self._paste_clipboard_image()
            return None

        if is_command_key("SEND_MESSAGE", key):
            self.send_stop_typing_status()
            if self.msg_body_edit_enabled:
                expanded = self._expand_attachments(self.msg_write_box.edit_text)
                if expanded is None:
                    return key
                self.msg_write_box.edit_text = expanded
            if self.compose_box_status == "open_with_stream":
                if re.fullmatch(r"\s*", self.title_write_box.edit_text):
                    topic = "(no topic)"
                else:
                    topic = self.title_write_box.edit_text

                if self.msg_edit_state is not None:
                    trimmed_topic = topic.strip()
                    # Trimmed topic must be compared since that is server check
                    if trimmed_topic == self.msg_edit_state.old_topic:
                        propagate_mode = "change_one"  # No change in topic
                    else:
                        propagate_mode = self.edit_mode_button.mode

                    args = dict(
                        message_id=self.msg_edit_state.message_id,
                        topic=topic,  # NOTE: Send untrimmed topic always for now
                        propagate_mode=propagate_mode,
                    )
                    if self.msg_body_edit_enabled:
                        args["content"] = self.msg_write_box.edit_text

                    success = self.model.update_stream_message(**args)
                else:
                    success = self.model.send_stream_message(
                        stream=self.stream_write_box.edit_text,
                        topic=topic,
                        content=self.msg_write_box.edit_text,
                    )
            else:
                if self.msg_edit_state is not None:
                    success = self.model.update_private_message(
                        content=self.msg_write_box.edit_text,
                        msg_id=self.msg_edit_state.message_id,
                    )
                else:
                    all_valid = self._tidy_valid_recipients_and_notify_invalid_ones(
                        self.to_write_box
                    )
                    if not all_valid:
                        return key
                    self.update_recipients(self.to_write_box)
                    if self.recipient_user_ids:
                        success = self.model.send_private_message(
                            recipients=self.recipient_user_ids,
                            content=self.msg_write_box.edit_text,
                        )
                    else:
                        self.view.controller.report_error(
                            ["Cannot send message without specifying recipients."]
                        )
                        success = None
            if success:
                self.msg_write_box.edit_text = ""
                if self.msg_edit_state is not None:
                    # Exit compose directly rather than routing EXIT_COMPOSE back
                    # through keypress: with the (vim) message body focused in
                    # insert mode, that key is intercepted to enter normal mode
                    # instead of exiting, which would leave msg_edit_state set
                    # (and trip the assert below, crashing the app on ctrl-d).
                    self.exit_compose_box()
                    assert self.msg_edit_state is None
        elif is_command_key("NARROW_MESSAGE_RECIPIENT", key):
            if self.compose_box_status == "open_with_stream":
                self.model.controller.narrow_to_topic(
                    stream_name=self.stream_write_box.edit_text,
                    topic_name=self.title_write_box.edit_text,
                    contextual_message_id=None,
                )
            elif self.compose_box_status == "open_with_private":
                self.recipient_emails = [
                    self.model.user_id_email_dict[user_id]
                    for user_id in self.recipient_user_ids
                ]
                if self.recipient_user_ids:
                    self.model.controller.narrow_to_user(
                        recipient_emails=self.recipient_emails,
                        contextual_message_id=None,
                    )
                else:
                    self.view.controller.report_error(
                        "Cannot narrow to message without specifying recipients."
                    )
        elif is_command_key("EXIT_COMPOSE", key):
            self.request_exit_compose()
        elif is_command_key("MARKDOWN_HELP", key):
            self.view.controller.show_markdown_help()
            return key
        elif is_command_key("OPEN_EXTERNAL_EDITOR", key):
            editor_command = self.view.controller.editor_command

            # None would indicate for shlex.split to read sys.stdin for Python < 3.12
            # It should never occur in practice
            assert isinstance(editor_command, str)

            if editor_command == "":
                self.view.controller.report_error(
                    "No external editor command specified; "
                    "Set 'editor' in zuliprc file, or "
                    "$ZULIP_EDITOR_COMMAND or $EDITOR environment variables."
                )
                return key

            editor_command_line: List[str] = shlex.split(editor_command)
            if not editor_command_line:
                fullpath_program = None  # A command may be specified, but empty
            else:
                fullpath_program = shutil.which(editor_command_line[0])
            if fullpath_program is None:
                self.view.controller.report_error(
                    "External editor command not found; "
                    "Check your zuliprc file, $EDITOR or $ZULIP_EDITOR_COMMAND."
                )
                return key
            editor_command_line[0] = fullpath_program

            with NamedTemporaryFile(suffix=".md") as edit_tempfile:
                with open(edit_tempfile.name, mode="w") as edit_writer:
                    edit_writer.write(self.msg_write_box.edit_text)
                self.view.controller.loop.screen.stop()

                editor_command_line.append(edit_tempfile.name)
                subprocess.call(editor_command_line)

                with open(edit_tempfile.name, mode="r") as edit_reader:
                    self.msg_write_box.edit_text = edit_reader.read().rstrip()
            self.view.controller.loop.screen.start()
            return key

        elif is_command_key("SAVE_AS_DRAFT", key):
            if self.msg_edit_state is None:
                if self.compose_box_status == "open_with_private":
                    all_valid = self._tidy_valid_recipients_and_notify_invalid_ones(
                        self.to_write_box
                    )
                    if not all_valid:
                        return key
                    self.update_recipients(self.to_write_box)
                    this_draft: Composition = PrivateComposition(
                        type="private",
                        to=self.recipient_user_ids,
                        content=self.msg_write_box.edit_text,
                        read_by_sender=True,
                    )
                elif self.compose_box_status == "open_with_stream":
                    this_draft = StreamComposition(
                        type="stream",
                        to=self.stream_write_box.edit_text,
                        content=self.msg_write_box.edit_text,
                        subject=self.title_write_box.edit_text,
                        read_by_sender=True,
                    )
                saved_draft = self.model.session_draft_message()
                if not saved_draft:
                    self.model.save_draft(this_draft)
                elif this_draft != saved_draft:
                    self.view.controller.save_draft_confirmation_popup(
                        this_draft,
                    )
        elif is_command_key("CYCLE_COMPOSE_FOCUS", key):
            if len(self.contents) == 0:
                return key
            header = self.header_write_box
            # toggle focus position
            if self.focus_position == self.FOCUS_CONTAINER_HEADER:
                if self.compose_box_status == "open_with_stream":
                    if header.focus_col == self.FOCUS_HEADER_BOX_STREAM:
                        if self.msg_edit_state is None:
                            stream_name = header[self.FOCUS_HEADER_BOX_STREAM].edit_text
                        else:
                            stream_name = header[self.FOCUS_HEADER_BOX_STREAM].text
                        if not self.model.is_valid_stream(stream_name):
                            invalid_stream_error = (
                                "Invalid stream name."
                                " Use {} or {} to autocomplete.".format(
                                    primary_display_key_for_command("AUTOCOMPLETE"),
                                    primary_display_key_for_command(
                                        "AUTOCOMPLETE_REVERSE"
                                    ),
                                )
                            )
                            self.view.controller.report_error([invalid_stream_error])
                            return key
                        user_ids = self.model.get_other_subscribers_in_stream(
                            stream_name=stream_name
                        )
                        self.recipient_user_ids = user_ids
                        self.stream_id = self.model.stream_id_from_name(stream_name)

                        header.focus_col = self.FOCUS_HEADER_BOX_TOPIC
                        return key
                    elif (
                        header.focus_col == self.FOCUS_HEADER_BOX_TOPIC
                        and self.msg_edit_state is not None
                    ):
                        header.focus_col = self.FOCUS_HEADER_BOX_EDIT
                        return key
                    elif header.focus_col == self.FOCUS_HEADER_BOX_EDIT:
                        if self.msg_body_edit_enabled:
                            header.focus_col = self.FOCUS_HEADER_BOX_STREAM
                            self.focus_position = self.FOCUS_CONTAINER_MESSAGE
                        else:
                            header.focus_col = self.FOCUS_HEADER_BOX_TOPIC
                        return key
                    else:
                        header.focus_col = self.FOCUS_HEADER_BOX_STREAM
                else:
                    all_valid = self._tidy_valid_recipients_and_notify_invalid_ones(
                        self.to_write_box
                    )
                    if not all_valid:
                        return key
                    # We extract recipients' user_ids and emails only once we know
                    # that all the recipients are valid, to avoid including any
                    # invalid ones.
                    self.update_recipients(self.to_write_box)

            if not self.msg_body_edit_enabled:
                return key
            if self.focus_position == self.FOCUS_CONTAINER_HEADER:
                self.focus_position = self.FOCUS_CONTAINER_MESSAGE
            else:
                self.focus_position = self.FOCUS_CONTAINER_HEADER
            if self.compose_box_status == "open_with_stream":
                if self.msg_edit_state is not None:
                    header.focus_col = self.FOCUS_HEADER_BOX_TOPIC
                else:
                    header.focus_col = self.FOCUS_HEADER_BOX_STREAM
            else:
                header.focus_col = self.FOCUS_HEADER_BOX_RECIPIENT

        key = super().keypress(size, key)

        # After the child edit box has processed the key, keep the footer in
        # sync with the message body (vim NORMAL indicator or live autocomplete
        # preview).
        self._update_message_body_footer(is_autocomplete_key)

        return key


class MessageSearchBox(urwid.Pile):
    """
    Search Box to search/control main list of messages
    """

    def __init__(self, controller: Any) -> None:
        self.controller = controller
        super().__init__(self.main_view())

    def main_view(self) -> Any:
        search_text = (
            f"Search [{', '.join(display_keys_for_command('SEARCH_MESSAGES'))}]: "
        )
        self.text_box = ReadlineEdit(f"{search_text} ")
        # Add some text so that when packing,
        # urwid doesn't hide the widget.
        self.conversation_focus = urwid.Text(" ")
        self.search_bar = urwid.Columns(
            [
                ("pack", self.conversation_focus),
                ("pack", urwid.Text(" ")),
                self.text_box,
            ]
        )
        self.msg_narrow = urwid.Text("DONT HIDE")
        self.recipient_bar = urwid.LineBox(
            self.msg_narrow,
            title="Current message recipients",
            **MESSAGE_RECIPIENTS_BORDER,
        )
        return [self.search_bar, self.recipient_bar]

    def keypress(self, size: urwid_Size, key: str) -> Optional[str]:
        if (
            is_command_key("EXECUTE_SEARCH", key) and self.text_box.edit_text == ""
        ) or is_command_key("CLEAR_SEARCH", key):
            self.text_box.set_edit_text("")
            self.controller.exit_editor_mode()
            self.controller.view.middle_column.set_focus("body")
            return key

        elif is_command_key("EXECUTE_SEARCH", key):
            self.controller.exit_editor_mode()
            self.controller.search_messages(self.text_box.edit_text)
            self.controller.view.middle_column.set_focus("body")
            return key

        key = super().keypress(size, key)
        return key


class PanelSearchBox(ReadlineEdit):
    """
    Search Box to search panel views in real-time.
    """

    def __init__(
        self, panel_view: Any, search_command: str, update_function: Callable[..., None]
    ) -> None:
        self.panel_view = panel_view
        self.search_command = search_command
        self.search_text = (
            f" Search [{', '.join(display_keys_for_command(search_command))}]: "
        )
        self.search_error = urwid.AttrMap(
            urwid.Text([" ", INVALID_MARKER, " No Results"]), "search_error"
        )
        urwid.connect_signal(self, "change", update_function)
        super().__init__(caption=self.search_text, edit_text="")

    def reset_search_text(self) -> None:
        self.set_caption(self.search_text)
        self.set_edit_text("")

    def valid_char(self, ch: str) -> bool:
        # This method 'strips' leading space *before* entering it in the box
        if self.edit_text:
            # Use regular validation if already have text
            return super().valid_char(ch)
        elif len(ch) != 1:
            # urwid expands some unicode to strings to be useful
            # (so we need to work around eg 'backspace')
            return False
        else:
            # Skip unicode 'Control characters' and 'space Zeperators'
            # This includes various invalid characters and complex spaces
            return unicodedata.category(ch) not in ("Cc", "Zs")

    def keypress(self, size: urwid_Size, key: str) -> Optional[str]:
        if (
            is_command_key("EXECUTE_SEARCH", key) and self.get_edit_text() == ""
        ) or is_command_key("CLEAR_SEARCH", key):
            self.panel_view.view.controller.exit_editor_mode()
            self.reset_search_text()
            self.panel_view.set_focus("body")
            # Don't call 'Esc' when inside a popup search-box.
            if not self.panel_view.view.controller.is_any_popup_open():
                self.panel_view.keypress(size, primary_key_for_command("CLEAR_SEARCH"))
        elif is_command_key("EXECUTE_SEARCH", key) and not self.panel_view.empty_search:
            self.panel_view.view.controller.exit_editor_mode()
            self.set_caption([("filter_results", " Search Results "), " "])
            self.panel_view.set_focus("body")
            if hasattr(self.panel_view, "log"):
                self.panel_view.body.set_focus(0)
        return super().keypress(size, key)
