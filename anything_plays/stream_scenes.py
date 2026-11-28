"""Reusable creator configurations, containing only Stream Mode style settings."""
import json
import re
from pathlib import Path

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.named_presets import validate_name
from anything_plays.portable_profiles import _reject_duplicate_keys

FORMAT = "anything-plays-stream-scene"
LIBRARY_FORMAT = "anything-plays-stream-scene-library"
VERSION = 1
MAX_BYTES = 64 * 1024
MAX_SCENES = 16

# All are ordinary existing compositor settings, not new capture devices.
STARTERS = {
    "Portrait recording": ("DS stacked", "30 FPS", 53, False, True),
    "Landscape stream": ("Side by side", "30 FPS", 60, False, True),
    "Camera spotlight": ("Side by side", "24 FPS", 30, False, True),
    "Clean gameplay": ("Side by side", "30 FPS", 70, False, False),
    "Low overhead": ("DS stacked", "15 FPS", 53, False, True),
}


def strict_scene(options, themes):
    """Reject rather than silently normalize untrusted scene documents."""
    if type(options) is not dict or set(options) != {
        "layout", "frame_rate", "theme", "border_color", "border_width",
        "game_size", "swap_screens", "show_labels",
    }:
        raise ValueError("Unexpected or missing scene fields.")
    for key, allowed in (
        ("layout", ("DS stacked", "Side by side")),
        ("frame_rate", ("15 FPS", "24 FPS", "30 FPS")),
        ("theme", themes),
    ):
        if type(options[key]) is not str or options[key] not in allowed:
            raise ValueError("Unsupported scene setting.")
    color = options["border_color"]
    if type(color) is not str or (color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color)):
        raise ValueError("Invalid scene border color.")
    for key, lo, hi in (("border_width", 2, 16), ("game_size", 30, 70)):
        if type(options[key]) is not int or not lo <= options[key] <= hi:
            raise ValueError("Invalid scene dimensions.")
    for key in ("swap_screens", "show_labels"):
        if type(options[key]) is not bool:
            raise ValueError("Invalid scene toggle.")
    result = dict(options)
    result["border_color"] = color.lower()
    return result


def starter_scene(name, current, themes):
    result = strict_scene(current, themes)
    if name not in STARTERS:
        raise ValueError("Unknown creator starter.")
    layout, rate, share, swap, labels = STARTERS[name]
    result.update(layout=layout, frame_rate=rate, game_size=share,
                  swap_screens=swap, show_labels=labels)
    return result


def _read_json(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Scene file exceeds its size limit.")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (ValueError, RecursionError, TypeError) as exc:
        raise ValueError("Invalid scene JSON.") from exc


def export_scene(path, options, themes):
    write_json_atomically(path, {"format": FORMAT, "version": VERSION,
                                 "options": strict_scene(options, themes)})


def import_scene(path, themes):
    document = _read_json(path)
    if (type(document) is not dict or set(document) != {"format", "version", "options"}
            or document["format"] != FORMAT or type(document["version"]) is not int
            or document["version"] != VERSION):
        raise ValueError("Unsupported scene document.")
    return strict_scene(document["options"], themes)


class SceneStore:
    def __init__(self, path, themes):
        self.path = Path(path)
        self.themes = tuple(themes)

    def entries(self):
        try:
            doc = _read_json(self.path)
        except FileNotFoundError:
            return {}
        if (type(doc) is not dict or set(doc) != {"format", "version", "scenes"}
                or doc["format"] != LIBRARY_FORMAT or type(doc["version"]) is not int
                or doc["version"] != VERSION or type(doc["scenes"]) is not dict
                or len(doc["scenes"]) > MAX_SCENES):
            raise ValueError("Invalid scene library.")
        clean, seen = {}, set()
        for name, options in doc["scenes"].items():
            if validate_name(name) != name or name.casefold() in seen:
                raise ValueError("Invalid or duplicate scene name.")
            seen.add(name.casefold())
            clean[name] = strict_scene(options, self.themes)
        return clean

    def _write(self, scenes):
        doc = {"format": LIBRARY_FORMAT, "version": VERSION, "scenes": scenes}
        if len((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")) > MAX_BYTES:
            raise ValueError("Scene library exceeds its size limit.")
        write_json_atomically(self.path, doc)

    def save(self, name, options, *, replace=False):
        name = validate_name(name)
        candidate = strict_scene(options, self.themes)
        scenes = self.entries()
        existing = next((key for key in scenes if key.casefold() == name.casefold()), None)
        if existing is not None:
            if not replace:
                raise ValueError("Scene name already exists.")
            del scenes[existing]
        elif len(scenes) >= MAX_SCENES:
            raise ValueError("Scene library is full.")
        scenes[name] = candidate
        self._write(scenes)
        return name

    def delete(self, name):
        scenes = self.entries()
        if name not in scenes:
            raise ValueError("Scene no longer exists.")
        del scenes[name]
        self._write(scenes)
