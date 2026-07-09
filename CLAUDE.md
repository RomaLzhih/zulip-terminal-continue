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
- `ui_tools/boxes.py: WriteBox._expand_attachments` — `@attach:<path>` token
  in the compose box (path runs to end of line, `~` expanded) uploads the file
  on send and becomes a markdown link; failed upload aborts the send with a
  footer error.
- `ui_tools/messages.py: unicode_emoji_from_code` — message-body emoji spans
  and unicode reactions render as real emoji glyphs; custom realm emoji keep
  the `:name:` text form. No variation selectors (VS16) — they break urwid's
  width math.

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
- No GitHub remote fork yet; `gh` is not installed on this machine.
