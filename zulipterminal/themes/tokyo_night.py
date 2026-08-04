"""
TOKYO NIGHT
-----------

The "night" (darkest) variant. Syntax highlighting uses a tokyo night pygments
style defined here, since pygments ships no tokyo night style of its own.

For further details on themefiles look at the theme contribution guide
"""

from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Escape,
    Generic,
    Keyword,
    Literal,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
)

from zulipterminal.config.color import Background
from zulipterminal.themes.colors_tokyo_night import DefaultBoldColor as Color


# fmt: off

class TokyoNightStyle(Style):
    """
    Tokyo Night syntax highlighting, following the palette's own editor
    highlight groups:
    https://github.com/folke/tokyonight.nvim
    """

    background_color = '#292e42'                # bg_highlight

    styles = {
        Text               : '#c0caf5',         # fg
        Whitespace         : '#3b4261',         # fg_gutter
        Escape             : '#e0af68',         # yellow
        Error              : '#f7768e',         # red

        # NOTE: tokyo night's own comment color (#565f89) drops below a 3:1
        # contrast ratio on the code background, so the brighter dark5 is used
        Comment            : '#737aa2 italic',  # dark5

        Keyword            : '#bb9af7',         # magenta
        Keyword.Constant   : '#ff9e64',         # orange
        Keyword.Type       : '#73daca',         # green1

        Operator           : '#7dcfff',         # cyan
        Punctuation        : '#a9b1d6',         # fg_dark

        Name               : '#c0caf5',         # fg
        Name.Attribute     : '#73daca',         # green1
        Name.Builtin       : '#f7768e',         # red
        Name.Class         : '#73daca',         # green1
        Name.Constant      : '#ff9e64',         # orange
        Name.Decorator     : '#7dcfff',         # cyan
        Name.Entity        : '#9d7cd8',         # purple
        Name.Exception     : '#f7768e',         # red
        Name.Function      : '#7aa2f7',         # blue
        Name.Label         : '#73daca',         # green1
        Name.Namespace     : '#73daca',         # green1
        Name.Tag           : '#f7768e',         # red
        Name.Variable      : '#c0caf5',         # fg

        Literal            : '#ff9e64',         # orange
        Number             : '#ff9e64',         # orange
        String             : '#9ece6a',         # green
        String.Doc         : '#737aa2 italic',  # dark5
        String.Escape      : '#e0af68',         # yellow
        String.Interpol    : '#e0af68',         # yellow

        Generic            : '#c0caf5',         # fg
        Generic.Deleted    : '#f7768e',         # red
        Generic.Emph       : '#c0caf5 italic',  # fg
        Generic.Error      : '#f7768e',         # red
        Generic.Heading    : '#7aa2f7 bold',    # blue
        Generic.Inserted   : '#9ece6a',         # green
        Generic.Output     : '#a9b1d6',         # fg_dark
        Generic.Prompt     : '#7aa2f7 bold',    # blue
        Generic.Strong     : '#c0caf5 bold',    # fg
        Generic.Subheading : '#7aa2f7 bold',    # blue
        Generic.Traceback  : '#f7768e',         # red
    }


STYLES = {
    # style_name       :  foreground                 background
    None               : (Color.FG,                 Background.COLOR),
    'selected'         : (Color.BG_DARK,            Color.BLUE),
    'msg_selected'     : (Color.FG,                 Color.FG_GUTTER),
    'header'           : (Color.BG_DARK,            Color.BLUE),
    'general_narrow'   : (Color.BG_DARK,            Color.BLUE),
    'general_bar'      : (Color.FG,                 Background.COLOR),
    'msg_sender'       : (Color.ORANGE__BOLD,       Background.COLOR),
    'unread'           : (Color.MAGENTA,            Background.COLOR),
    'user_active'      : (Color.GREEN,              Background.COLOR),
    'user_idle'        : (Color.YELLOW,             Background.COLOR),
    'user_offline'     : (Color.FG_DARK,            Background.COLOR),
    'user_inactive'    : (Color.DARK5,              Background.COLOR),
    'user_bot'         : (Color.GREEN1,             Background.COLOR),
    'title'            : (Color.FG__BOLD,           Background.COLOR),
    'column_title'     : (Color.FG__BOLD,           Background.COLOR),
    'time'             : (Color.CYAN,               Background.COLOR),
    'bar'              : (Color.FG,                 Color.FG_GUTTER),
    'msg_emoji'        : (Color.MAGENTA,            Background.COLOR),
    'reaction'         : (Color.MAGENTA__BOLD,      Background.COLOR),
    'reaction_mine'    : (Color.BG_DARK,            Color.MAGENTA),
    'msg_heading'      : (Color.BG_DARK__BOLD,      Color.PURPLE),
    'msg_math'         : (Color.FG,                 Color.BG_HIGHLIGHT),
    'msg_mention'      : (Color.RED__BOLD,          Background.COLOR),
    'msg_link'         : (Color.BLUE,               Background.COLOR),
    'msg_link_index'   : (Color.BLUE__BOLD,         Background.COLOR),
    'msg_quote'        : (Color.YELLOW,             Background.COLOR),
    'msg_bold'         : (Color.FG__BOLD,           Background.COLOR),
    'msg_time'         : (Color.BG_DARK,            Color.FG_DARK),
    'footer'           : (Color.BG_DARK,            Color.FG_DARK),
    'footer_contrast'  : (Color.FG,                 Background.COLOR),
    'starred'          : (Color.YELLOW__BOLD,       Background.COLOR),
    'unread_count'     : (Color.ORANGE,             Background.COLOR),
    'starred_count'    : (Color.DARK5,              Background.COLOR),
    'table_head'       : (Color.FG__BOLD,           Background.COLOR),
    'filter_results'   : (Color.BG_DARK,            Color.GREEN),
    'edit_topic'       : (Color.FG,                 Color.TERMINAL_BLACK),
    'edit_tag'         : (Color.FG,                 Color.TERMINAL_BLACK),
    'edit_author'      : (Color.ORANGE,             Background.COLOR),
    'edit_time'        : (Color.CYAN,               Background.COLOR),
    'current_user'     : (Color.DARK5,              Background.COLOR),
    'muted'            : (Color.DARK5,              Background.COLOR),
    'popup_border'     : (Color.BLUE,               Background.COLOR),
    'popup_category'   : (Color.CYAN__BOLD,         Background.COLOR),
    'popup_contrast'   : (Color.FG,                 Color.FG_GUTTER),
    'popup_important'  : (Color.RED__BOLD,          Background.COLOR),
    'widget_disabled'  : (Color.COMMENT,            Background.COLOR),
    'area:help'        : (Color.BG_DARK,            Color.GREEN),
    'area:msg'         : (Color.BG_DARK,            Color.MAGENTA),
    'area:stream'      : (Color.BG_DARK,            Color.BLUE),
    'area:error'       : (Color.BG_DARK,            Color.RED),
    'area:user'        : (Color.BG_DARK,            Color.YELLOW),
    'search_error'     : (Color.RED,                Background.COLOR),
    'task:success'     : (Color.BG_DARK,            Color.GREEN),
    'task:error'       : (Color.BG_DARK,            Color.RED),
    'task:warning'     : (Color.BG_DARK,            Color.YELLOW),
    'ui_code'          : (Color.FG,                 Color.BG_HIGHLIGHT),
}

META = {
    'background': Color.BG,
    'pygments': {
        'styles'    : TokyoNightStyle().styles,
        'background': 'h236',                    # bg_highlight
        # NOTE: Unlike 'styles', these are not translated into urwid format,
        # so they are written using urwid's own syntax.
        'overrides' : {
            'c'   : '#737aa2,italics',           # dark5
            'cp'  : '#bb9af7',                   # magenta
            'cpf' : '#737aa2',                   # dark5
            'err' : '#f7768e',                   # red
            'n'   : '#c0caf5',                   # fg
            'p'   : '#a9b1d6',                   # fg_dark
            'w'   : '#c0caf5',                   # inline/plain-codeblock: fg
        }
    }
}
# fmt: on
