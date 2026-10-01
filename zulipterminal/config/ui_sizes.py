"""
Fixed sizes of UI elements
"""

TAB_WIDTH = 3
LEFT_WIDTH = 31
RIGHT_WIDTH = 23

# These affect popup width-scaling, dependent upon window width
# At and below this width, popup is window width:
MIN_SUPPORTED_POPUP_WIDTH = 80
# Until this width, popup scales linearly upwards with width
MAX_LINEAR_SCALING_WIDTH = 100
# Above that width, popup increases as 3/4 of window width

# The emoji picker is as wide as its longest entry, but only up to this width:
# a few emojis have a dozen aliases, which would stretch it across the window
MAX_EMOJI_PICKER_WIDTH = 80
