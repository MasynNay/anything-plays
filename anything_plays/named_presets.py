"""Local, bounded named control presets, using the portable profile schema.

Names are local labels only. Stored profiles use the existing portable
allowlist, never private paths, artwork, device identities or game data.
"""
import copy
import json
from pathlib import Path

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.portable_profiles import (
    _reject_duplicate_keys, make_bundle, parse_bundle, MAX_FILE_BYTES,
)
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM

FORMAT = "anything-plays-named-presets"
VERSION = 1
MAX_LIBRARY_BYTES = 2 * 1024 * 1024
MAX_PRESETS_PER_CONSOLE = 12


def validate_name(name):
    if type(name) is not str:
        raise ValueError("Enter a preset name.")
    name = name.strip()
    if not 1 <= len(name) <= 48 or not name.isprintable():
        raise ValueError("Use 1–48 printable characters for the name.")
    return name


class NamedPresetStore:
    """Read a validated library; fail closed on corruption, never overwrite it."""

    def __init__(self, path, allowed_themes):
        self.path = Path(path)
        self.allowed_themes = tuple(allowed_themes)

    def _read(self):
        try:
            with self.path.open("rb") as stream:
                raw = stream.read(MAX_LIBRARY_BYTES + 1)
        except FileNotFoundError:
            return {}
        if len(raw) > MAX_LIBRARY_BYTES:
            raise ValueError("Preset library exceeds its size limit.")
        try:
            doc = json.loads(raw.decode("utf-8"),
                             object_pairs_hook=_reject_duplicate_keys)
        except (ValueError, RecursionError, TypeError) as exc:
            raise ValueError("Preset library could not be validated.") from exc
        if (type(doc) is not dict or set(doc) != {"format", "version", "presets"}
                or doc["format"] != FORMAT or type(doc["version"]) is not int
                or doc["version"] != VERSION or type(doc["presets"]) is not dict):
            raise ValueError("Unsupported preset library format.")
        clean = {}
        for system, entries in doc["presets"].items():
            if (system not in BUTTONS_BY_SYSTEM or type(entries) is not dict
                    or len(entries) > MAX_PRESETS_PER_CONSOLE):
                raise ValueError("Invalid console preset collection.")
            normalized = {}
            seen = set()
            for name, bundle in entries.items():
                if validate_name(name) != name or name.casefold() in seen:
                    raise ValueError("Invalid or duplicate preset name.")
                seen.add(name.casefold())
                if type(bundle) is not dict or bundle.get("format") is None:
                    raise ValueError("Invalid stored preset.")
                data = json.dumps(bundle, ensure_ascii=False, allow_nan=False)
                profile, theme, legacy = parse_bundle(
                    data, selected_system=system, allowed_themes=self.allowed_themes,
                )
                if legacy:
                    raise ValueError("Invalid stored preset version.")
                normalized[name] = make_bundle(
                    system, profile, theme=theme, allowed_themes=self.allowed_themes,
                )
            clean[system] = normalized
        return clean

    def _write(self, entries):
        doc = {"format": FORMAT, "version": VERSION, "presets": entries}
        size = len((json.dumps(doc, indent=2, ensure_ascii=False,
                               allow_nan=False) + "\n").encode("utf-8"))
        if size > MAX_LIBRARY_BYTES:
            raise ValueError("Preset library exceeds its size limit.")
        write_json_atomically(self.path, doc)

    def list(self, system):
        if system not in BUTTONS_BY_SYSTEM:
            raise ValueError("Unknown console.")
        return tuple(sorted(self._read().get(system, {}), key=str.casefold))

    def get(self, system, name):
        name = validate_name(name)
        if system not in BUTTONS_BY_SYSTEM:
            raise ValueError("Unknown console.")
        try:
            return copy.deepcopy(self._read()[system][name])
        except KeyError:
            raise ValueError("Preset no longer exists.") from None

    def save(self, system, name, profile, *, theme=None, replace=False):
        name = validate_name(name)
        bundle = make_bundle(system, profile, theme=theme,
                             allowed_themes=self.allowed_themes)
        if len(json.dumps(bundle, ensure_ascii=False).encode("utf-8")) > MAX_FILE_BYTES:
            raise ValueError("Preset exceeds the portable profile size limit.")
        all_entries = self._read()
        entries = all_entries.setdefault(system, {})
        existing = next((key for key in entries
                         if key.casefold() == name.casefold()), None)
        if existing is not None:
            if not replace:
                raise ValueError("A preset with that name already exists.")
            del entries[existing]
        elif len(entries) >= MAX_PRESETS_PER_CONSOLE:
            raise ValueError("This console already has 12 presets.")
        entries[name] = bundle
        self._write(all_entries)
        return name

    def delete(self, system, name):
        name = validate_name(name)
        if system not in BUTTONS_BY_SYSTEM:
            raise ValueError("Unknown console.")
        all_entries = self._read()
        if name not in all_entries.get(system, {}):
            raise ValueError("Preset no longer exists.")
        del all_entries[system][name]
        if not all_entries[system]:
            del all_entries[system]
        self._write(all_entries)
