"""
NORD
----

Syntax highlighting follows nord's own syntax guidelines, via a pygments style
defined here, since pygments ships no nord style of its own.

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
from zulipterminal.themes.colors_nord import DefaultBoldColor as Color


# fmt: off

class NordStyle(Style):
    """
    Nord syntax highlighting, following the palette's syntax guidelines:
    https://www.nordtheme.com/docs/colors-and-palettes
    """

    background_color = '#3b4252'                # nord1

    styles = {
        Text               : '#d8dee9',         # nord4
        Whitespace         : '#4c566a',         # nord3
        Escape             : '#ebcb8b',         # nord13
        Error              : '#bf616a',         # nord11

        Comment            : '#8b98b0 italic',  # darkened nord4

        Keyword            : '#81a1c1',         # nord9
        Keyword.Constant   : '#b48ead',         # nord15
        Keyword.Type       : '#8fbcbb',         # nord7

        Operator           : '#81a1c1',         # nord9
        Punctuation        : '#eceff4',         # nord6

        Name               : '#d8dee9',         # nord4
        Name.Attribute     : '#8fbcbb',         # nord7
        Name.Builtin       : '#88c0d0',         # nord8
        Name.Class         : '#8fbcbb',         # nord7
        Name.Constant      : '#d8dee9',         # nord4
        Name.Decorator     : '#d08770',         # nord12
        Name.Entity        : '#8fbcbb',         # nord7
        Name.Exception     : '#bf616a',         # nord11
        Name.Function      : '#88c0d0',         # nord8
        Name.Label         : '#8fbcbb',         # nord7
        Name.Namespace     : '#8fbcbb',         # nord7
        Name.Tag           : '#81a1c1',         # nord9
        Name.Variable      : '#d8dee9',         # nord4

        Literal            : '#b48ead',         # nord15
        Number             : '#b48ead',         # nord15
        String             : '#a3be8c',         # nord14
        String.Doc         : '#8b98b0 italic',  # darkened nord4
        String.Escape      : '#ebcb8b',         # nord13
        String.Interpol    : '#ebcb8b',         # nord13

        Generic            : '#d8dee9',         # nord4
        Generic.Deleted    : '#bf616a',         # nord11
        Generic.Emph       : '#d8dee9 italic',  # nord4
        Generic.Error      : '#bf616a',         # nord11
        Generic.Heading    : '#88c0d0 bold',    # nord8
        Generic.Inserted   : '#a3be8c',         # nord14
        Generic.Output     : '#d8dee9',         # nord4
        Generic.Prompt     : '#88c0d0 bold',    # nord8
        Generic.Strong     : '#d8dee9 bold',    # nord4
        Generic.Subheading : '#88c0d0 bold',    # nord8
        Generic.Traceback  : '#bf616a',         # nord11
    }


STYLES = {
    # style_name       :  foreground                background
    None               : (Color.SNOW0,             Background.COLOR),
    'selected'         : (Color.NIGHT0,            Color.FROST_CYAN),
    'msg_selected'     : (Color.SNOW0,             Color.NIGHT2),
    'header'           : (Color.NIGHT0,            Color.FROST_BLUE),
    'general_narrow'   : (Color.NIGHT0,            Color.FROST_BLUE),
    'general_bar'      : (Color.SNOW0,             Background.COLOR),
    'msg_sender'       : (Color.ORANGE__BOLD,      Background.COLOR),
    'unread'           : (Color.PURPLE,            Background.COLOR),
    'user_active'      : (Color.GREEN,             Background.COLOR),
    'user_idle'        : (Color.YELLOW,            Background.COLOR),
    'user_offline'     : (Color.SNOW0,             Background.COLOR),
    'user_inactive'    : (Color.SNOW0_DIM,         Background.COLOR),
    'user_bot'         : (Color.FROST_GREEN,       Background.COLOR),
    'title'            : (Color.SNOW2__BOLD,       Background.COLOR),
    'column_title'     : (Color.SNOW2__BOLD,       Background.COLOR),
    'time'             : (Color.FROST_CYAN,        Background.COLOR),
    'bar'              : (Color.SNOW0,             Color.NIGHT2),
    'msg_emoji'        : (Color.PURPLE,            Background.COLOR),
    'reaction'         : (Color.PURPLE__BOLD,      Background.COLOR),
    'reaction_mine'    : (Color.NIGHT0,            Color.PURPLE),
    'msg_heading'      : (Color.NIGHT0__BOLD,      Color.FROST_GREEN),
    'msg_math'         : (Color.SNOW0,             Color.NIGHT1),
    'msg_mention'      : (Color.RED__BOLD,         Background.COLOR),
    'msg_link'         : (Color.FROST_BLUE,        Background.COLOR),
    'msg_link_index'   : (Color.FROST_BLUE__BOLD,  Background.COLOR),
    'msg_quote'        : (Color.YELLOW,            Background.COLOR),
    'msg_bold'         : (Color.SNOW2__BOLD,       Background.COLOR),
    'msg_time'         : (Color.NIGHT0,            Color.SNOW0),
    'footer'           : (Color.NIGHT0,            Color.SNOW0),
    'footer_contrast'  : (Color.SNOW0,             Background.COLOR),
    'starred'          : (Color.YELLOW__BOLD,      Background.COLOR),
    'unread_count'     : (Color.ORANGE,            Background.COLOR),
    'starred_count'    : (Color.SNOW0_DIM,         Background.COLOR),
    'table_head'       : (Color.SNOW2__BOLD,       Background.COLOR),
    'filter_results'   : (Color.NIGHT0,            Color.GREEN),
    'edit_topic'       : (Color.SNOW0,             Color.NIGHT2),
    'edit_tag'         : (Color.SNOW0,             Color.NIGHT2),
    'edit_author'      : (Color.ORANGE,            Background.COLOR),
    'edit_time'        : (Color.FROST_CYAN,        Background.COLOR),
    'current_user'     : (Color.SNOW0_DIM,         Background.COLOR),
    'muted'            : (Color.SNOW0_DIM,         Background.COLOR),
    'popup_border'     : (Color.FROST_CYAN,        Background.COLOR),
    'popup_category'   : (Color.FROST_BLUE__BOLD,  Background.COLOR),
    'popup_contrast'   : (Color.SNOW0,             Color.NIGHT2),
    'popup_important'  : (Color.RED__BOLD,         Background.COLOR),
    'widget_disabled'  : (Color.NIGHT3_BRIGHT,     Background.COLOR),
    'area:help'        : (Color.NIGHT0,            Color.GREEN),
    'area:msg'         : (Color.NIGHT0,            Color.PURPLE),
    'area:stream'      : (Color.NIGHT0,            Color.FROST_BLUE),
    'area:error'       : (Color.NIGHT0,            Color.RED),
    'area:user'        : (Color.NIGHT0,            Color.YELLOW),
    'search_error'     : (Color.RED,               Background.COLOR),
    'task:success'     : (Color.NIGHT0,            Color.GREEN),
    'task:error'       : (Color.NIGHT0,            Color.RED),
    'task:warning'     : (Color.NIGHT0,            Color.YELLOW),
    'ui_code'          : (Color.SNOW0,             Color.NIGHT1),
}

META = {
    'background': Color.NIGHT0,
    'pygments': {
        'styles'    : NordStyle().styles,
        'background': 'h238',                    # nord1
        # NOTE: Unlike 'styles', these are not translated into urwid format,
        # so they are written using urwid's own syntax.
        'overrides' : {
            'c'   : '#8b98b0,italics',           # darkened nord4
            'cp'  : '#5e81ac',                   # nord10
            'cpf' : '#8b98b0',                   # darkened nord4
            'err' : '#bf616a',                   # nord11
            'n'   : '#d8dee9',                   # nord4
            'p'   : '#eceff4',                   # nord6
            'w'   : '#d8dee9',                   # inline/plain-codeblock: nord4
        }
    }
}
# fmt: on
