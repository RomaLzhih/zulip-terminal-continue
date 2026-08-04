"""
COLORS FOR TOKYO NIGHT THEMES
-----------------------------
Contains color definitions or functions common across tokyo night themes.
For further details on themefiles look at the theme contribution guide.

This file uses the palette of the "night" (darkest) variant. For color
reference see:
    https://github.com/folke/tokyonight.nvim/blob/main/extras/lua/tokyonight_night.lua

NOTE: The 16-color aliases are picked for what each color *means* (green ->
light_green) rather than by nearest RGB match, so the theme still reads
correctly on a 16-color terminal. The 256-color codes are the nearest xterm-256
approximations; a terminal running with `--color-depth 24bit` gets the exact
tokyo night colors.
"""
from enum import Enum

from zulipterminal.config.color import color_properties


# fmt: off

class TokyoNightColor(Enum):
    # color        =  16code          256code   24code

    # Backgrounds, darkest first
    BG_DARK        = 'black           h234      #16161e'
    BG             = 'black           h235      #1a1b26'
    BG_HIGHLIGHT   = 'black           h236      #292e42'

    # Raised areas - selected rows, code blocks, input fields
    FG_GUTTER      = 'dark_gray       h239      #3b4261'
    TERMINAL_BLACK = 'dark_gray       h240      #414868'

    # Dimmed text
    COMMENT        = 'dark_gray       h60       #565f89'
    DARK5          = 'dark_gray       h67       #737aa2'

    # Foregrounds
    FG_DARK        = 'light_gray      h146      #a9b1d6'
    FG             = 'white           h189      #c0caf5'

    # Accents - cool
    BLUE           = 'light_blue      h111      #7aa2f7'
    CYAN           = 'light_cyan      h117      #7dcfff'
    GREEN1         = 'light_cyan      h80       #73daca'
    GREEN          = 'light_green     h149      #9ece6a'

    # Accents - warm
    YELLOW         = 'yellow          h179      #e0af68'
    ORANGE         = 'brown           h215      #ff9e64'
    RED            = 'light_red       h210      #f7768e'

    # Accents - purples
    MAGENTA        = 'light_magenta   h141      #bb9af7'
    PURPLE         = 'light_magenta   h140      #9d7cd8'


# fmt: on


DefaultBoldColor = color_properties(TokyoNightColor, "BOLD")
