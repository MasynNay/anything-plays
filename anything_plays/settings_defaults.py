"""Legacy-compatible tracking defaults used when creating console profiles."""

from anything_plays.gba_emulator import BUTTONS

DEFAULT = {
    'rgb': [255, 0, 0], 'tolerance': 20, 'min_area': 120,
    'hold_frames': 8, 'cooldown_ms': 450, 'mirror': False,
    'zone_font_size': 50, 'zone_opacity': 90, 'zone_style': 'Bold',
    'zone_border_width': 6, 'zone_label_position': 'Center',
    'zone_image': '', 'shuffle_enabled': True,
    'zones': {
        'Left': [0.00000000, 0.00000000, 0.33333333, 0.33333333],
        'Up': [0.33333333, 0.00000000, 0.66666667, 0.33333333],
        'Right': [0.66666667, 0.00000000, 1.00000000, 0.33333333],
        'A': [0.00000000, 0.33333333, 0.33333333, 0.66666667],
        'Start': [0.33333333, 0.33333333, 0.66666667, 0.66666667],
        'B': [0.66666667, 0.33333333, 1.00000000, 0.66666667],
        'Down': [0.00000000, 0.66666667, 0.33333333, 1.00000000],
        'Select': [0.33333333, 0.66666667, 0.66666667, 1.00000000],
        'Shuffle': [0.66666667, 0.66666667, 1.00000000, 1.00000000],
    },
    'mapping': {name: name for name in BUTTONS}
}


ACTIVE_BUTTONS = tuple(BUTTONS)
