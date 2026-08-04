"""
COLORS FOR CATPPUCCIN THEMES
----------------------------
Contains color definitions or functions common across catppuccin themes.
For further details on themefiles look at the theme contribution guide.

This file uses the official catppuccin palette (the Mocha flavor).
For color reference see:
    https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md

NOTE: The 16-color aliases are picked for what each color *means* (green ->
light_green) rather than by nearest RGB match, so the theme still reads
correctly on a 16-color terminal. The 256-color codes are the nearest xterm-256
approximations, which wash the palette out somewhat; a terminal running with
`--color-depth 24bit` gets the exact catppuccin colors.
"""
from enum import Enum

from zulipterminal.config.color import color_properties


# fmt: off

class CatppuccinMochaColor(Enum):
    # color      =  16code          256code   24code

    # Base - backgrounds, darkest first
    CRUST        = 'black           h233      #11111b'
    MANTLE       = 'black           h234      #181825'
    BASE         = 'black           h235      #1e1e2e'

    # Surfaces - raised areas (selected rows, code blocks, input fields)
    SURFACE0     = 'black           h237      #313244'
    SURFACE1     = 'dark_gray       h239      #45475a'
    SURFACE2     = 'dark_gray       h241      #585b70'

    # Overlays - dimmed text (muted, disabled, comments)
    OVERLAY0     = 'dark_gray       h243      #6c7086'
    OVERLAY1     = 'dark_gray       h245      #7f849c'
    OVERLAY2     = 'light_gray      h247      #9399b2'

    # Text - foregrounds, dimmest first
    SUBTEXT0     = 'light_gray      h146      #a6adc8'
    SUBTEXT1     = 'light_gray      h188      #bac2de'
    TEXT         = 'white           h189      #cdd6f4'

    # Accents - blues
    LAVENDER     = 'light_blue      h147      #b4befe'
    BLUE         = 'light_blue      h111      #89b4fa'
    SAPPHIRE     = 'light_cyan      h117      #74c7ec'
    SKY          = 'light_cyan      h116      #89dceb'
    TEAL         = 'light_cyan      h122      #94e2d5'

    # Accents - warm
    GREEN        = 'light_green     h151      #a6e3a1'
    YELLOW       = 'yellow          h223      #f9e2af'
    PEACH        = 'brown           h216      #fab387'
    MAROON       = 'light_red       h181      #eba0ac'
    RED          = 'light_red       h211      #f38ba8'

    # Accents - pinks
    MAUVE        = 'light_magenta   h183      #cba6f7'
    PINK         = 'light_magenta   h218      #f5c2e7'
    # NOTE: flamingo and rosewater are near-identical in 256-color mode
    FLAMINGO     = 'light_red       h224      #f2cdcd'
    ROSEWATER    = 'white           h224      #f5e0dc'


# fmt: on


DefaultBoldColor = color_properties(CatppuccinMochaColor, "BOLD")
