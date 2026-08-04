# CLAUDE.md

## What this repository is

Personal fork of [zulip/zulip-terminal](https://github.com/zulip/zulip-terminal)
(the upstream repo is actively committed to, but has had no PyPI release since
0.7.0 in 2021 — hence the fork). We maintain our own features and fixes here.

- `main` tracks pristine upstream — keep it clean so upstream can be pulled
  and merged into `dev`.
- `dev` is the working branch carrying our patches. New work goes here.

## How it is installed / run

Installed **editable** into Homebrew Python 3.10:

```sh
/opt/homebrew/opt/python@3.10/bin/python3.10 -m pip install -e .
```

`zulip-term` (in `/opt/homebrew/bin`) therefore imports directly from this
repo — code edits take effect on the next `zulip-term` restart, no reinstall.
Credentials/config come from `~/zuliprc` (email / API key / site). The tmux
unread indicator (`~/.config/tmux/zulip-unread.sh`) reads the same file.

## Local patches on dev (beyond upstream)

- `model.py: Model._resync_unread_counts` — after a dead event queue is
  re-registered (post-sleep), re-register with `fetch_data=True` and repaint
  all unread-count widgets. Fixes counts frozen until restart.
- `model.py: poll_for_events` / `_start_presence_updates` — network errors
  from `get_events` / the presence ping are caught and retried instead of
  killing the daemon thread. Post-sleep, a dead socket raises
  `zulip.UnrecoverableNetworkError` (no retry in the client); previously the
  thread died, its traceback hit stderr (uncaptured) and corrupted the urwid
  screen, and events stopped until restart. `_resync_unread_counts` now also
  calls `loop.screen.clear()` so the first draw after reconnect repaints
  every cell (auto ctrl-l), wiping any stray terminal output.
- `helper.py: set_count` / `_recount_aggregate_unreads` — the aggregate
  counts (`all_msg`, `all_pms`) are recomputed from the per-conversation
  keyed counts (same muting rules as `classify_unread_counts`) on every
  count change, instead of drifting via incremental `+= / -=` in
  `_set_count_in_view`. Fixes "All messages" showing phantom unreads after
  all streams/PMs were read.
- `ui_tools/boxes.py: WriteBox._expand_attachments` — `@attach:<path>` token
  in the compose box (path runs to end of line, `~` expanded) uploads the file
  on send and becomes a markdown link; failed upload aborts the send with a
  footer error. Documented for users in the Help menu via an "Attachments"
  category appended in `ui_tools/views.py: HelpView.__init__` (it is a compose
  token, not a keybinding, so it is not in `KEY_BINDINGS`). The token prefix is
  the `ATTACH_TOKEN_PREFIX` constant, shared with the path completer below.
- `helper.py: clipboard_image_to_file` + `ui_tools/boxes.py:
  WriteBox._paste_clipboard_image` — `PASTE_IMAGE` (ctrl v) pastes an image
  **from the system clipboard** into the compose box: the clipboard image is
  written to a temp PNG and an `@attach:<path>` token is inserted at the
  cursor, so the existing `_expand_attachments` path uploads it on send. A
  terminal paste only ever delivers text, hence reading the clipboard
  ourselves. Per-platform, since the clipboard is a GUI resource: MacOS uses
  `osascript` (always present; the AppleScript needs an `on run argv` handler
  for argv to exist, and writes the file itself so the bytes never cross a
  pipe as text), Linux tries `wl-paste` then `xclip` (stdout is the PNG), WSL
  uses `powershell.exe`. **Only the MacOS path is verified on this machine.**
  The temp file is `image.png` inside a `mkdtemp` folder — `_expand_attachments`
  labels the link with the basename, so the folder (not the file) carries the
  uniqueness and recipients see `[image.png](...)` rather than a random temp
  name. No image in the clipboard reports a footer error and leaves no folder
  behind.
- `ui_tools/messages.py: unicode_emoji_from_code` — message-body emoji spans
  and unicode reactions render as real emoji glyphs; custom realm emoji keep
  the `:name:` text form. No variation selectors (VS16) — they break urwid's
  width math.
- `ui_tools/boxes.py: WriteBox._refresh_autocomplete_footer_preview` — live
  autocomplete preview in the message body: as you type a `@`/`#`/`:` token
  (the whitespace-delimited word at the cursor), candidates appear in the
  footer automatically, without pressing AUTOCOMPLETE (ctrl f). The preview
  lists matches with nothing selected (`state=None`); ctrl f still cycles and
  inserts as before. Wired from `WriteBox.keypress` after the child edit box
  handles the key (skipped for the AUTOCOMPLETE keys so it can't clobber the
  highlighted selection).
- `ui_tools/boxes.py: WriteBox.autocomplete_users` — when composing to a stream
  (`compose_box_status == "open_with_stream"`), `@`-mention suggestions are
  filtered to that channel's subscribers (`recipient_user_ids`); non-members are
  hidden since mentioning them does not notify. Private compose is unaffected
  (shows all users).
- `ui_tools/boxes.py: VimEditBox` — the message body is a modal (vim-like)
  editor. Starts in **insert** mode (types exactly like `ReadlineEdit`); `esc`
  enters **normal** mode, a second `esc` exits compose (`esc` handling lives in
  `WriteBox.keypress`, since it intercepts `EXIT_COMPOSE` before the child).
  Normal mode maps a basic subset onto ReadlineEdit primitives: `h j k l w b
  0 $ gg G`, `i a I A o O`, `x D dd dw C u p`, and the `c` change operator
  (`cc cw cb c$ c0` = delete + enter insert); unknown keys are swallowed. The
  footer shows a `NORMAL` indicator (`WriteBox._set_vim_normal_mode_footer` /
  `_update_message_body_footer`). Only `msg_write_box` is a `VimEditBox`; the
  To/topic/stream header boxes stay plain `ReadlineEdit`. Documented for users
  in the Help menu ("Compose: Vim mode" category in `HelpView.__init__`).
  The `SEND_MESSAGE` edit path calls `exit_compose_box()` directly rather than
  re-issuing `EXIT_COMPOSE` through `keypress`: with the body focused in insert
  mode that key is intercepted into normal mode instead of exiting, so
  `msg_edit_state` stayed set and the following `assert ... is None` raised,
  escaping `keypress` and closing the whole app on `ctrl d` (send) while
  editing. Regressed by `test_keypress_SEND_MESSAGE_edit_in_insert_mode_exits_without_crash`
  (uses a real `VimEditBox`, unlike the mock-based `SEND_MESSAGE` tests that
  missed it).
- `model.py: Model.group_pm_conversations` + `ui_tools/views.py:
  RightColumnView.update_user_list` / `users_view` — the users panel search
  (`w`) also surfaces **group DM** conversations. Typing a name lists the
  matching individual users (each opens the 1:1 DM) followed by any group DMs
  that include a matching participant, so one search finds both the 1:1 and
  the group threads with someone. Group DMs come from the server's
  `recent_private_conversations` (now requested in `initial_data_to_fetch`;
  `.get(..., [])` tolerates older servers), keyed into `unread_huddles` (which
  includes oneself) for the unread count; 1:1 conversations are skipped since
  they already appear as users. Each group is a `buttons.py: GroupPMButton`
  (mirrors `UserButton._narrow_with_compose`, narrowing via `narrow_to_user`
  with all recipient emails). Matching uses `helper.py: match_group_pm` (same
  prefix rule as `match_user`, across every participant). Groups appear only
  while searching; the default panel and the presence-refresh path are
  unchanged.
- `ui_tools/messages.py: MessageBox.soup2markup` (`img` branch) — a bare `<img>`
  in a message body (shown as `[IMAGE NOT RENDERED]`) now registers its `src` in
  `message_links` (resolved to an absolute URL) and renders the placeholder
  tagged with the link index, `[IMAGE NOT RENDERED][N]`. Previously the src was
  dropped, so such an image had no entry in the Message Information popup (`i`)
  and could not be opened at all. Inline image previews (inside a
  `message_inline_image` div) are unchanged — that div is not recursed, so its
  inner `<a>`/`<img>` never reach this branch; those images stay openable via
  their accompanying text link. Opening any of these links flows through the
  upstream `process_media`, which downloads the file and opens it in the OS
  default app (`open`/`xdg-open`/`explorer.exe`). (Inline in-terminal image
  rendering via the Kitty graphics protocol was tried and removed — it was
  unreliable in the user's tmux setup; images open externally instead.)
- `ui_tools/buttons.py: MessageLinkButton.handle_link` — external web links in
  the Message Information popup (`i`) now open in the default graphical browser.
  Previously `handle_link` only handled Zulip-internal narrow links and
  `/user_uploads/` media; any other URL fell through and did nothing. The added
  `else` branch closes the popup (so the footer status is visible) and calls
  `controller.open_in_browser(self.link)` (`core.py: Controller.open_in_browser`,
  which uses `webbrowser`). Keyboard-driven, so it works regardless of the
  terminal's mouse-capture/URL-click behavior.
- `ui_tools/views.py: StreamsView.toggle_topics` + `ui_tools/buttons.py:
  StreamButton.keypress` — a stream's topics expand **inline**, indented
  directly under it in the stream list, instead of the upstream full-panel
  swap to a separate Topics view. `enter` on a stream narrows to the whole
  stream (all messages) *and* toggles its topics open/closed, keeping focus in
  the stream list (activation no longer jumps to the message column) so a topic
  can be picked next; `t` (`TOGGLE_TOPIC`) toggles the topics without narrowing;
  `enter` on an inline topic narrows to it as before (then `c` composes with
  that stream+topic prefilled). Each inline topic is a `TopicButton` wrapped in
  `urwid.Padding(left=2)`; only one stream is expanded at a time, and the
  expansion is dropped on stream search (`update_streams` / `CLEAR_SEARCH`)
  since those rebuild the list from `streams_btn_list`, which never holds the
  inline rows. `_narrow_to` only rewrites the center message log, so the
  inline rows survive the narrow. The upstream full-panel `TopicsView` /
  `LeftColumnView.show_topic_view` path is retained but now dormant
  (`is_in_topic_view` is never set true, so the topic-rename refresh in
  `model.py` that depended on it no longer fires — new topics show on the next
  expand). Tested in `tests/ui/test_ui_tools.py::TestStreamsView`
  (`test_toggle_topics_*`) and `tests/ui_tools/test_buttons.py::TestStreamButton`
  (`test_keypress_TOGGLE_TOPIC_expands_inline`,
  `test_keypress_ACTIVATE_BUTTON_narrows_and_expands`).
- `ui_tools/views.py: HelpView.update_help_list` / `HelpView.keypress` — the
  Help menu (`?`) has a **live search**: press `/` to filter entries as you
  type (matching each binding's description *and* its keys), `enter` to browse
  the results, `esc`/`q`/`?` to close. Mirrors the emoji-picker popup search — a
  `PanelSearchBox` in the header, with `@asynch update_help_list` rebuilding
  `contents["body"]` from the stored `help_menu_content`. It reuses the global
  `SEARCH_MESSAGES` (`/`) command rather than a dedicated `SEARCH_HELP`, because
  a second `/` in the "Searching" help category trips the `lint-hotkeys`
  duplicate-key check (and the popup's own search box already shows the `/`
  hint, so a separate documented row would be redundant). `HelpView` sets
  `self.view = controller.view` so the shared `PanelSearchBox` can reach the
  controller (`panel_view.view.controller`). Tested in `tests/ui_tools/
  test_popups.py::TestHelpView` (`test_keypress_SEARCH_HELP_enters_search_mode`,
  `test_update_help_list_filters_to_matches`,
  `test_update_help_list_no_match_shows_error`).
- `core.py: Controller.restart` + `ui.py: View.keypress` — `RESTART` (`ctrl x`)
  restarts the app **in place**: deregisters the event queue, stops the urwid
  screen (restoring the terminal), then re-execs the same command with
  `os.execv(sys.executable, [sys.executable, *sys.argv])`, replacing this
  process. Lets edited code (the editable install) or a fresh session take
  effect without manually quitting and relaunching. No confirmation prompt, but
  `View.keypress` only reaches global commands when **not** in editor mode, so
  it cannot fire mid-compose (no draft loss). `screen.stop()` from within a
  keypress is the same pattern `OPEN_EXTERNAL_EDITOR` already uses. Tested by
  `tests/core/test_core.py::TestController::test_restart` and
  `tests/ui/test_ui.py::TestView::test_keypress_RESTART`.
- `ui_tools/buttons.py: EmojiButton.__init__` — the emoji reaction picker (`:`)
  shows the actual **glyph** prefixed before each unicode emoji's name (e.g.
  `👍  +1, thumbs_up`) instead of name-only text. The glyph is produced by the
  reused `ui_tools/messages.py: unicode_emoji_from_code`, gated on the emoji's
  `type == "unicode_emoji"` (looked up in `model.active_emoji_data`); custom /
  realm and zulip-extra emojis keep their `:name:` text — their `code` is a realm
  id / `"zulip"`, not a codepoint, and would otherwise mis-parse as hex into a
  stray glyph. The name/aliases stay in the label, so the picker's search (which
  matches `button.emoji_name` / `button.aliases`, not the label) is unaffected.
  `buttons.py` importing `messages.py` is cycle-free (messages' import chain
  never reaches buttons). Tested in `tests/ui_tools/test_buttons.py`
  (`test_init_unicode_emoji_prefixes_glyph`, `test_init_realm_emoji_keeps_text`).
- `model.py: Model._handle_reaction_event` / `Model.get_user_id_from_reaction` —
  a reaction added to a message now appears **immediately**, instead of only
  after narrowing away and back. The `add` branch built its stored reaction with
  `event.get(key)` over a fixed key list, so on a server that no longer sends the
  deprecated `user` object (superseded by `user_id` in Zulip v3.0, ZFL 2) it
  stored `"user": None`. `get_user_id_from_reaction` used
  `reaction.get("user", {})`, which returns `None` for a present-but-empty key
  (only a *missing* key yields the `{}` default), so its `assert isinstance(user,
  dict)` failed. That assertion is swallowed by the blanket `except Exception:
  return None` in `ui_tools/messages.py: MessageBox.reactions_view`, which
  dropped the entire reactions row — silently, until a re-narrow re-fetched the
  message from the server and overwrote the poisoned entry. (The same assertion
  is *not* guarded on the `remove` branch, so un-reacting raised into
  `zulip-terminal-thread-exceptions.log`.) Fixed at both ends: the event handler
  copies only keys the event actually carries (`if key in event`), and
  `get_user_id_from_reaction` treats an empty `user` as absent
  (`reaction.get("user") or {}`). Tested by
  `tests/model/test_model.py::TestModel::test__handle_reaction_event_add_stores_identifiable_user`
  and `tests/ui_tools/test_messages.py::TestMessageBox::test_reactions_view_renders_user_id_only_reaction`
  (the pre-existing `test_reactions_view` mocks `get_user_id_from_reaction`, so
  it could not catch this).
- `model.py: Model._update_rendered_view` — the "message no longer belongs in
  this narrow" check treated *any* two-element narrow as a topic narrow and
  compared `message["subject"]` against `narrow[1][1]`. In a **search** narrow
  (`[["stream", s], ["search", q]]`, or the DM equivalent) that second term is
  the query, never a subject, so any re-render of a message while viewing search
  results — a reaction, an edit, a flag change — dropped it from the view. Now
  also requires `narrow[1][0] == "topic"`. Tested by the added
  `msgbox_updated_in_stream_search_narrow` / `msgbox_updated_in_pm_search_narrow`
  / `search_narrow_is_not_a_topic_narrow` cases in
  `tests/model/test_model.py::TestModel::test__update_rendered_view*`.
- `core.py: Controller.cancel_compose_on_quit` + `ui_tools/boxes.py:
  WriteBox.request_exit_compose` — `QUIT` (`ctrl c`) with the
  compose box open now **closes the compose box** instead of quitting the app,
  from vim insert mode as well as normal mode (where `esc` only leaves insert
  mode, so exiting took two keys). Everywhere else `ctrl c` still quits as
  before. The hook has to live in the SIGINT handlers (`no_prompt_exit_handler`
  / `prompting_exit_handler`), not in `WriteBox.keypress`: the terminal turns
  `ctrl c` into SIGINT (urwid uses cbreak mode, which leaves `ISIG` on), so it
  never arrives as a keypress — `QUIT` is listed in `KEY_BINDINGS` purely as
  documentation and `is_command_key("QUIT", ...)` is never called. The compose
  box is identified by `controller._editor is view.write_box` (`WriteBox`
  registers *itself* as the editor in `set_editor_mode`). The EXIT_COMPOSE body
  was extracted into `WriteBox.request_exit_compose` so both paths share the
  long-unsaved-message confirmation popup. Tested in
  `tests/core/test_core.py::TestController` (`test_cancel_compose_on_quit__*`,
  `test_exit_handler_cancels_compose_instead_of_quitting`, plus the two
  still-quits-when-not-composing tests) and
  `tests/ui_tools/test_boxes.py::TestWriteBox::test_request_exit_compose_closes_compose_from_insert_mode`.
- `ui_tools/boxes.py: WriteBox.autocomplete_path` — `@attach:<path>` tokens get
  **shell-style path completion**: candidates preview in the footer as you type
  and `AUTOCOMPLETE` (ctrl f) cycles/inserts them, like mentions and emojis.
  The typed path is split at its last `/` into a directory to list and a partial
  name matched case-insensitively; directories complete with a trailing `/` (so
  the next completion descends), dotfiles appear only once the partial name
  starts with `.`, and a bare `~` completes to `~/`. The directory is otherwise
  left exactly as typed rather than expanded, matching `_expand_attachments`
  (which expands `~` and resolves relative paths against the working directory).
  Dispatched at the top of `generic_autocomplete`, *before* its prefix map:
  `@attach:` contains both `@` and `:`, and that map picks the **right-most**
  prefix, so the `:` would otherwise offer emojis for what is a path. Because a
  path runs to the end of the line, `_refresh_autocomplete_footer_preview` finds
  the token with `line.rfind(ATTACH_TOKEN_PREFIX)` instead of using the last
  whitespace-delimited word, so paths containing spaces still preview (`ctrl f`
  was already unaffected — `DELIMS_MESSAGE_COMPOSE` is only `\t\n;`). Tested in
  `tests/ui_tools/test_boxes.py::TestWriteBox` (`test_autocomplete_path*`,
  `test_generic_autocomplete_path`,
  `test__refresh_autocomplete_footer_preview_path_with_space`) against a real
  `tmp_path` tree.
- `model.py: Model._handle_message_event` — a message **we** sent scrolls into
  view automatically: after appending it to the log, the message view is focused
  on it. Appending alone only reveals the new message when the focus already
  happens to sit on the previously last message (urwid's ListBox fills the rows
  below the focus widget); with the focus higher up — the common case, since
  narrowing focuses the first *unread* message — it lands below the fold and had
  to be scrolled to by hand. Gated on `message["sender_id"] == self.user_id`:
  moving the view for someone else's message would yank the reader away
  mid-read. No mark-as-read fallout, since our own messages arrive already
  flagged `read`, so `MessageView.read_message` (run via `ModListWalker`'s focus
  action) stops immediately instead of walking up over unread messages.
  Reactions need no equivalent: the reacted message is by definition the focused
  one, and urwid already reflows so its new reaction row stays visible —
  verified by rendering real `MessageBox` widgets in a `ModListWalker` listbox
  before and after the swap `_update_rendered_view` performs. Tested by
  `tests/model/test_model.py::TestModel::test__handle_message_event_scrolls_to_own_message`.
- `themes/catppuccin_mocha.py` + `themes/colors_catppuccin.py` — a
  **Catppuccin Mocha** theme, registered in `config/themes.py: THEMES` (no
  alias: that table is explicitly closed to additions) and listed in
  `docs/FAQ.md`. The palette file carries the official hex values; the 16-color
  aliases are chosen for what each color *means* (`GREEN -> light_green`) rather
  than by nearest RGB, since a nearest-match puts catppuccin's pastel green in
  the `light_gray` slot — gruvbox's palette does the same. The 256-color codes
  are nearest-xterm approximations, computed against the h-code table in
  `themes/THEME_CONTRIBUTING.md`, and are deliberately distinct per color so
  shades stay separable at that depth. Pygments ships no catppuccin style, so
  `CatppuccinMochaStyle` is defined in the theme file (subclassing
  `pygments.style.Style`, whose metaclass fills in every token in
  `STANDARD_TYPES` — a hand-rolled dict would `KeyError` in
  `generate_pygments_styles`). `META["pygments"]["overrides"]` is *not* run
  through `STYLE_TRANSLATIONS`, so those entries are written in urwid syntax
  (`'#6c7086,italics'`) while `styles` uses pygments syntax (`'#6c7086 italic'`).
  Every fg/bg pair was checked for WCAG contrast against the base: the lowest
  are the intentionally-dim `widget_disabled` (3.4:1) and `muted` /
  `user_inactive` (4.4:1); the median is 8.9:1.
  **~/zuliprc now sets `theme=catppuccin_mocha` and `color-depth=24bit`** (the
  default 256-color depth washes this palette out; tmux reports `RGB` in
  `client_termfeatures` here, so true color works). Backup at
  `~/zuliprc.bak-before-catppuccin`. Registered in
  `tests/config/test_themes.py: expected_complete_themes`, which enforces style
  completeness and color-code validity.
- `themes/nord.py` + `themes/colors_nord.py`, `themes/tokyo_night.py` +
  `themes/colors_tokyo_night.py` — **Nord** and **Tokyo Night** (the "night"
  variant), built to the same recipe as catppuccin above: official hex values,
  semantic 16-color aliases, distinct nearest-xterm 256 codes, and a pygments
  `Style` subclass per theme (neither ships with pygments) following each
  palette's own syntax guidelines. Both are registered in `THEMES` and in the
  tests' `expected_complete_themes`, and appear in the `T` picker automatically.
  Two deliberate deviations, both driven by a WCAG contrast audit of every
  fg/bg pair and every syntax token against the code background:
  * `colors_nord.py: SNOW0_DIM` (`#8b98b0`) is **not core nord**. Nord's
    darkest usable greys (nord3, and nord-vim's nord3_bright) manage only
    2.4:1 against nord0, where the other bundled dark themes sit at 4.1-4.5:1
    for muted/inactive/current-user text; this is nord4 darkened to match.
    `NIGHT3_BRIGHT` is kept for `widget_disabled`, where dim is the point.
  * `tokyo_night.py` uses `dark5` rather than tokyo night's own `comment`
    (`#565f89`) for code comments, which drops to 2.4:1 on the code background.

  Still below 3:1 by choice: `widget_disabled` in both (disabled should read as
  disabled), and nord's red-family syntax tokens at 2.46:1 - that is nord11 on
  nord1, the pairing every Nord editor port uses, so it is kept faithful.
  The same audit found catppuccin's comments at 2.6:1, so those moved from
  `overlay0` to `overlay2` - which is also what catppuccin's own VSCode port
  uses.
- `core.py: Controller.set_theme` / `show_theme_picker` + `ui_tools/views.py:
  ThemePickerView` + `ui_tools/buttons.py: ThemeButton` — `SWITCH_THEME` (`T`)
  opens a picker that **switches theme without restarting**. The theme applies
  the moment an entry is activated and the popup stays open (the active marker
  moves, focus is kept), so themes can be compared against the messages behind
  it; `esc`/`T` closes, keeping whatever is applied. Session-only by design —
  `theme` in zuliprc still decides what the next run starts with. It works
  because urwid canvases store style *names*, not escape sequences:
  `screen.register_palette()` rebuilds `raw_display.Screen._pal_escape`, which
  `draw_screen` consults per cell, so no widget needs rebuilding. The catch is
  that urwid only rewrites cells whose *content* changed, so `screen.clear()`
  is needed to force a full repaint — the same trick `_resync_unread_counts`
  uses post-sleep. `set_theme` also updates `self.theme_name`, which the About
  popup displays. Tested in `tests/core/test_core.py` (`test_set_theme`,
  `test_show_theme_picker`), `tests/ui/test_ui.py`
  (`test_keypress_SWITCH_THEME`), `tests/ui_tools/test_popups.py:
  TestThemePickerView`, and `tests/ui_tools/test_buttons.py: TestThemeButton`.

## Testing

```sh
/opt/homebrew/opt/python@3.10/bin/python3.10 -m pytest -q --no-cov
```

- `--no-cov` (or installed pytest-cov) is needed: pyproject.toml passes
  coverage args unconditionally.
- **4 pre-existing failures** in `tests/cli/test_run.py`
  (`test_main_multiple_autohide_options`, `test_main_multiple_notify_options`)
  exist on pristine upstream in this environment (argparse help-text parsing).
  Ignore them; anything else failing is real.
- When changing behavior, update the corresponding upstream test rather than
  deleting it (see `test_poll_for_events__reconnect_ok` for an example).

## Conventions

- Follow upstream commit style: `area: Imperative summary.` (e.g.
  `model: Resync unread counts after re-registering a dead event queue.`)
- Python 3.7-compatible syntax (upstream still supports 3.7); run on 3.10.
- Remotes: `origin` = git@github.com:RomaLzhih/zulip-terminal-continue.git (our fork),
  `upstream` = https://github.com/zulip/zulip-terminal.git. `gh` is not
  installed on this machine.
