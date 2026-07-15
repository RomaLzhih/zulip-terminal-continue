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
  token, not a keybinding, so it is not in `KEY_BINDINGS`).
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
- `helper.py: process_media` + `core.py: Controller.render_image_in_terminal` /
  `_render_pending_image` — opening an uploaded **image** (via the message-info
  popup `i`, `/user_uploads/` link) now renders it **inside the terminal**
  instead of only launching an external app. `helper.py: in_terminal_image_command`
  autodetects a renderer (`$ZULIP_IMAGE_RENDERER` override, else chafa / kitty
  `+kitten icat` / wezterm `imgcat` / viu / timg); chafa is preferred because it
  uses the Kitty/sixel/iTerm graphics protocols where available and otherwise
  truecolor block chars, which also work through tmux. `helper.py: is_image_path`
  gates on extension; non-images (and the case where no renderer is installed)
  fall back to the existing `open_media` external-app path. `process_media` is
  `@asynch` (runs in a worker thread), so the screen takeover is marshaled onto
  the main urwid thread via a dedicated `watch_pipe` (`_image_render_pipe`) and
  an `Event` (`_image_render_done`) that blocks the worker until the render
  finishes; `_render_pending_image` does `screen.stop()` → draw → wait for Enter
  → `screen.start()` (same suspend/restore pattern as the external editor in
  `boxes.py`). True inline thumbnails in the scrolling message list are not
  attempted (urwid's cell grid + tmux make Kitty-protocol placement unreliable);
  this is a full-window preview.
- `ui_tools/buttons.py: MessageLinkButton.handle_link` — external web links in
  the Message Information popup (`i`) now open in the default graphical browser.
  Previously `handle_link` only handled Zulip-internal narrow links and
  `/user_uploads/` media; any other URL fell through and did nothing. The added
  `else` branch closes the popup (so the footer status is visible) and calls
  `controller.open_in_browser(self.link)` (`core.py: Controller.open_in_browser`,
  which uses `webbrowser`). Keyboard-driven, so it works regardless of the
  terminal's mouse-capture/URL-click behavior.

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
