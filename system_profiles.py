"""Persistent per-console camera-zone profiles (no ROM or emulator state)."""
import copy
import json
from pathlib import Path

BUTTONS_BY_SYSTEM = {
    'gb': ('Left', 'Up', 'Right', 'A', 'Start', 'B', 'Down', 'Select'),
    'gbc': ('Left', 'Up', 'Right', 'A', 'Start', 'B', 'Down', 'Select'),
    'gba': ('Left', 'Up', 'Right', 'A', 'Start', 'B', 'Down', 'Select', 'L', 'R'),
    'snes': ('Left', 'Up', 'Right', 'A', 'Start', 'B', 'Down', 'Select', 'X', 'Y', 'L', 'R'),
}

DISABLED_MAPPING = '(None)'

def enabled_zones(profile, system):
    """Only enabled console zones are eligible for drawing and input."""
    mappings = profile.get('mapping', {})
    return [name for name in BUTTONS_BY_SYSTEM[system]
            if mappings.get(name, name) != DISABLED_MAPPING]

def fit_to_grid(profile, system):
    """Arrange enabled buttons in equal cells, with centered final row.

    Existing rectangles for disabled buttons are preserved so they can be
    re-enabled later. Shuffle is a separate optional zone, not a button.
    """
    import math
    names = enabled_zones(profile, system)
    if not names:
        return profile
    cols = math.ceil(math.sqrt(len(names)))
    rows = math.ceil(len(names) / cols)
    zones = profile.setdefault('zones', {})
    for index, name in enumerate(names):
        row, col = divmod(index, cols)
        row_count = min(cols, len(names) - row * cols)
        # Center a partially populated row without distorting cell dimensions.
        offset = (cols - row_count) / 2
        x = (col + offset) / cols
        zones[name] = [x, row / rows, (col + offset + 1) / cols, (row + 1) / rows]
    return profile

def default_for(system, base):
    """Generate independent layouts; never mutate the supplied base profile."""
    profile = copy.deepcopy(base)
    names = BUTTONS_BY_SYSTEM[system]
    # Fill equal-size grid cells, keeping the occupied pattern horizontally
    # symmetrical. A missing cell is left empty rather than stretching a zone.
    count = len(names) + 1  # Optional Shuffle zone also has a grid cell.
    cols, rows = (3, 3) if count == 9 else ((3, 4) if count == 11 else (5, 3))
    profile['zones'] = {}
    positions = []
    full_rows, remainder = divmod(count, cols)
    for row in range(full_rows):
        positions.extend((col, row) for col in range(cols))
    if remainder:
        # Center the final row. With two cells in a 3-column row, leave
        # the middle empty so the left/right occupancy remains symmetrical.
        if cols == 3 and remainder == 2:
            last_cols = (0, 2)
        else:
            start = (cols - remainder) // 2
            last_cols = range(start, start + remainder)
        positions.extend((col, full_rows) for col in last_cols)
    for name, (col, row) in zip((*names, 'Shuffle'), positions):
        profile['zones'][name] = [col / cols, row / rows, (col + 1) / cols, (row + 1) / rows]
    profile['mapping'] = {name: name for name in names}
    return profile

def normalize(system, profile, base):
    """Upgrade old profiles while retaining existing zone sizes and positions."""
    default = default_for(system, base)
    if not isinstance(profile, dict):
        return default
    for key, value in profile.items():
        if key not in ('zones', 'mapping'):
            default[key] = copy.deepcopy(value)
    zones = profile.get('zones', {})
    mapping = profile.get('mapping', {})
    if isinstance(zones, dict):
        for name in default['zones']:
            rect = zones.get(name)
            if (isinstance(rect, (list, tuple)) and len(rect) == 4
                    and all(isinstance(v, (float, int)) and not isinstance(v, bool) for v in rect)
                    and 0 <= rect[0] < rect[2] <= 1 and 0 <= rect[1] < rect[3] <= 1):
                default['zones'][name] = list(rect)
    if isinstance(mapping, dict):
        for name in default['mapping']:
            if mapping.get(name) in (*BUTTONS_BY_SYSTEM[system], DISABLED_MAPPING):
                default['mapping'][name] = mapping[name]
    return default

class ProfileStore:
    def __init__(self, path, base):
        self.path = Path(path)
        self.base = base
        self.profiles = {}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                self.profiles = {k: normalize(k, v, base) for k, v in data.items() if k in BUTTONS_BY_SYSTEM}
        except (OSError, ValueError, TypeError):
            pass

    def get(self, system):
        return copy.deepcopy(self.profiles.get(system, default_for(system, self.base)))

    def put(self, system, profile):
        self.profiles[system] = normalize(system, profile, self.base)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.profiles, indent=2), encoding='utf-8')
        temporary.replace(self.path)
