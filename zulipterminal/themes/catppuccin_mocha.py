"""
CATPPUCCIN MOCHA
----------------

The darkest of the four catppuccin flavors. Syntax highlighting uses a
catppuccin pygments style defined here, since pygments ships no catppuccin
style of its own.

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
from zulipterminal.themes.colors_catppuccin import DefaultBoldColor as Color


# fmt: off

class CatppuccinMochaStyle(Style):
    """
    Catppuccin Mocha syntax highlighting, following the palette's style guide:
    https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md
    """

    background_color = '#313244'                # surface0

    styles = {
        Text               : '#cdd6f4',         # text
        Whitespace         : '#585b70',         # surface2
        Escape             : '#f5c2e7',         # pink
        Error              : '#f38ba8',         # red

        Comment            : '#9399b2 italic',  # overlay2

        Keyword            : '#cba6f7',         # mauve
        Keyword.Constant   : '#fab387',         # peach
        Keyword.Type       : '#f9e2af',         # yellow

        Operator           : '#89dceb',         # sky
        Punctuation        : '#9399b2',         # overlay2

        Name               : '#cdd6f4',         # text
        Name.Attribute     : '#89b4fa',         # blue
        Name.Builtin       : '#f38ba8',         # red
        Name.Class         : '#f9e2af',         # yellow
        Name.Constant      : '#fab387',         # peach
        Name.Decorator     : '#89b4fa',         # blue
        Name.Entity        : '#f5c2e7',         # pink
        Name.Exception     : '#f9e2af',         # yellow
        Name.Function      : '#89b4fa',         # blue
        Name.Label         : '#94e2d5',         # teal
        Name.Namespace     : '#f9e2af',         # yellow
        Name.Tag           : '#cba6f7',         # mauve
        Name.Variable      : '#cdd6f4',         # text

        Literal            : '#fab387',         # peach
        Number             : '#fab387',         # peach
        String             : '#a6e3a1',         # green
        String.Doc         : '#9399b2 italic',  # overlay2
        String.Escape      : '#f5c2e7',         # pink
        String.Interpol    : '#f5c2e7',         # pink

        Generic            : '#cdd6f4',         # text
        Generic.Deleted    : '#f38ba8',         # red
        Generic.Emph       : '#cdd6f4 italic',  # text
        Generic.Error      : '#f38ba8',         # red
        Generic.Heading    : '#89b4fa bold',    # blue
        Generic.Inserted   : '#a6e3a1',         # green
        Generic.Output     : '#a6adc8',         # subtext0
        Generic.Prompt     : '#89b4fa bold',    # blue
        Generic.Strong     : '#cdd6f4 bold',    # text
        Generic.Subheading : '#89b4fa bold',    # blue
        Generic.Traceback  : '#f38ba8',         # red
    }


STYLES = {
    # style_name       :  foreground                background
    None               : (Color.TEXT,              Background.COLOR),
    'selected'         : (Color.CRUST,             Color.LAVENDER),
    'msg_selected'     : (Color.TEXT,              Color.SURFACE1),
    'header'           : (Color.BASE,              Color.BLUE),
    'general_narrow'   : (Color.CRUST,             Color.BLUE),
    'general_bar'      : (Color.TEXT,              Background.COLOR),
    'msg_sender'       : (Color.PEACH__BOLD,       Background.COLOR),
    'unread'           : (Color.MAUVE,             Background.COLOR),
    'user_active'      : (Color.GREEN,             Background.COLOR),
    'user_idle'        : (Color.YELLOW,            Background.COLOR),
    'user_offline'     : (Color.SUBTEXT0,          Background.COLOR),
    'user_inactive'    : (Color.OVERLAY1,          Background.COLOR),
    'user_bot'         : (Color.SAPPHIRE,          Background.COLOR),
    'title'            : (Color.TEXT__BOLD,        Background.COLOR),
    'column_title'     : (Color.TEXT__BOLD,        Background.COLOR),
    'time'             : (Color.SAPPHIRE,          Background.COLOR),
    'bar'              : (Color.TEXT,              Color.SURFACE1),
    'msg_emoji'        : (Color.PINK,              Background.COLOR),
    'reaction'         : (Color.PINK__BOLD,        Background.COLOR),
    'reaction_mine'    : (Color.CRUST,             Color.PINK),
    'msg_heading'      : (Color.CRUST__BOLD,       Color.MAUVE),
    'msg_math'         : (Color.TEXT,              Color.SURFACE0),
    'msg_mention'      : (Color.RED__BOLD,         Background.COLOR),
    'msg_link'         : (Color.BLUE,              Background.COLOR),
    'msg_link_index'   : (Color.BLUE__BOLD,        Background.COLOR),
    'msg_quote'        : (Color.YELLOW,            Background.COLOR),
    'msg_bold'         : (Color.TEXT__BOLD,        Background.COLOR),
    'msg_time'         : (Color.CRUST,             Color.OVERLAY2),
    'footer'           : (Color.CRUST,             Color.SUBTEXT0),
    'footer_contrast'  : (Color.TEXT,              Background.COLOR),
    'starred'          : (Color.YELLOW__BOLD,      Background.COLOR),
    'unread_count'     : (Color.PEACH,             Background.COLOR),
    'starred_count'    : (Color.OVERLAY2,          Background.COLOR),
    'table_head'       : (Color.TEXT__BOLD,        Background.COLOR),
    'filter_results'   : (Color.CRUST,             Color.GREEN),
    'edit_topic'       : (Color.TEXT,              Color.SURFACE2),
    'edit_tag'         : (Color.TEXT,              Color.SURFACE2),
    'edit_author'      : (Color.PEACH,             Background.COLOR),
    'edit_time'        : (Color.SAPPHIRE,          Background.COLOR),
    'current_user'     : (Color.SUBTEXT0,          Background.COLOR),
    'muted'            : (Color.OVERLAY1,          Background.COLOR),
    'popup_border'     : (Color.LAVENDER,          Background.COLOR),
    'popup_category'   : (Color.BLUE__BOLD,        Background.COLOR),
    'popup_contrast'   : (Color.TEXT,              Color.SURFACE1),
    'popup_important'  : (Color.RED__BOLD,         Background.COLOR),
    'widget_disabled'  : (Color.OVERLAY0,          Background.COLOR),
    'area:help'        : (Color.CRUST,             Color.GREEN),
    'area:msg'         : (Color.CRUST,             Color.MAUVE),
    'area:stream'      : (Color.CRUST,             Color.BLUE),
    'area:error'       : (Color.CRUST,             Color.RED),
    'area:user'        : (Color.CRUST,             Color.YELLOW),
    'search_error'     : (Color.RED,               Background.COLOR),
    'task:success'     : (Color.CRUST,             Color.GREEN),
    'task:error'       : (Color.CRUST,             Color.RED),
    'task:warning'     : (Color.CRUST,             Color.YELLOW),
    'ui_code'          : (Color.TEXT,              Color.SURFACE0),
}

META = {
    'background': Color.BASE,
    'pygments': {
        'styles'    : CatppuccinMochaStyle().styles,
        'background': 'h237',                    # surface0
        # NOTE: Unlike 'styles', these are not translated into urwid format,
        # so they are written using urwid's own syntax.
        'overrides' : {
            'c'   : '#9399b2,italics',           # overlay2
            'cp'  : '#f5c2e7',                   # pink
            'cpf' : '#9399b2',                   # overlay2
            'err' : '#f38ba8',                   # red
            'n'   : '#cdd6f4',                   # text
            'p'   : '#9399b2',                   # overlay2
            'w'   : '#cdd6f4',                   # inline/plain-codeblock: text
        }
    }
}
# fmt: on
