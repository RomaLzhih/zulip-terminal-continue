"""
COLORS FOR NORD THEMES
----------------------
Contains color definitions or functions common across nord themes.
For further details on themefiles look at the theme contribution guide.

This file uses the official nord palette. For color reference see:
    https://www.nordtheme.com/docs/colors-and-palettes

NOTE: The 16-color aliases are picked for what each color *means* (green ->
light_green) rather than by nearest RGB match, so the theme still reads
correctly on a 16-color terminal. The 256-color codes are the nearest xterm-256
approximations; a terminal running with `--color-depth 24bit` gets the exact
nord colors.
"""
from enum import Enum

from zulipterminal.config.color import color_properties


# fmt: off

class NordColor(Enum):
    # color        =  16code          256code   24code

    # Polar Night - backgrounds and dimmed text (nord0-nord3)
    NIGHT0         = 'black           h237      #2e3440'
    NIGHT1         = 'black           h238      #3b4252'
    NIGHT2         = 'dark_gray       h239      #434c5e'
    NIGHT3         = 'dark_gray       h240      #4c566a'
    # nord-vim's lightened nord3; nord3 itself is too dark to read as text
    NIGHT3_BRIGHT  = 'dark_gray       h60       #616e88'
    # Also not core nord: de-emphasised UI text and comments. nord3_bright
    # manages only 2.4:1 against nord0, where the other bundled dark themes
    # sit at 4.1-4.5:1 for the same role; this is nord4 darkened to match.
    SNOW0_DIM      = 'light_gray      h103      #8b98b0'

    # Snow Storm - foregrounds (nord4-nord6)
    SNOW0          = 'light_gray      h254      #d8dee9'
    SNOW1          = 'white           h255      #e5e9f0'
    SNOW2          = 'white           h231      #eceff4'

    # Frost - the blue-green accents (nord7-nord10)
    FROST_GREEN    = 'light_cyan      h109      #8fbcbb'
    FROST_CYAN     = 'light_cyan      h116      #88c0d0'
    FROST_BLUE     = 'light_blue      h110      #81a1c1'
    FROST_DEEP     = 'dark_blue       h67       #5e81ac'

    # Aurora - the colorful accents (nord11-nord15)
    RED            = 'light_red       h131      #bf616a'
    ORANGE         = 'brown           h173      #d08770'
    YELLOW         = 'yellow          h222      #ebcb8b'
    GREEN          = 'light_green     h150      #a3be8c'
    PURPLE         = 'light_magenta   h139      #b48ead'


# fmt: on


DefaultBoldColor = color_properties(NordColor, "BOLD")
