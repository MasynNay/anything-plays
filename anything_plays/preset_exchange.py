"""Versioned, user-selected collections of portable control layouts.

Collection labels are explicitly shared by the user. Local preset names
are not exported automatically. No network access or active profile writes.
"""
import json
from pathlib import Path

from anything_plays.atomic_storage import write_json_atomically
from anything_plays.named_presets import validate_name
from anything_plays.portable_profiles import _reject_duplicate_keys, parse_bundle, make_bundle
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM

FORMAT = "anything-plays-preset-collection"
VERSION = 1
MAX_COLLECTION_BYTES = 512 * 1024
MAX_COLLECTION_ENTRIES = 48


def validate_collection(document, allowed_themes):
    if (type(document) is not dict
            or set(document) != {"format", "version", "layouts"}
            or document["format"] != FORMAT
            or type(document["version"]) is not int
            or document["version"] != VERSION
            or type(document["layouts"]) is not list
            or not 1 <= len(document["layouts"]) <= MAX_COLLECTION_ENTRIES):
        raise ValueError("Invalid or unsupported preset collection.")
    clean = []
    seen = set()
    for item in document["layouts"]:
        if type(item) is not dict or set(item) != {"label", "bundle"}:
            raise ValueError("Invalid collection entry.")
        label = validate_name(item["label"])
        if label != item["label"]:
            raise ValueError("Invalid collection label.")
        bundle = item["bundle"]
        if type(bundle) is not dict or type(bundle.get("system")) is not str:
            raise ValueError("Missing console identity.")
        system = bundle["system"]
        if system not in BUTTONS_BY_SYSTEM:
            raise ValueError("Unsupported console.")
        identity = (system, label.casefold())
        if identity in seen:
            raise ValueError("Duplicate collection label for a console.")
        seen.add(identity)
        try:
            raw = json.dumps(bundle, ensure_ascii=False, allow_nan=False)
            profile, theme, legacy = parse_bundle(
                raw, selected_system=system, allowed_themes=allowed_themes,
            )
        except (ValueError, TypeError, OverflowError, RecursionError) as exc:
            raise ValueError("Invalid portable controls in collection.") from exc
        if legacy:
            raise ValueError("Collections require versioned portable profiles.")
        clean.append({"label": label, "bundle": make_bundle(
            system, profile, theme=theme, allowed_themes=allowed_themes,
        )})
    return {"format": FORMAT, "version": VERSION, "layouts": clean}


def read_collection(path, allowed_themes):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_COLLECTION_BYTES + 1)
    if len(raw) > MAX_COLLECTION_BYTES:
        raise ValueError("Collection is too large.")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("Invalid collection JSON.") from exc
    return validate_collection(document, allowed_themes)


def write_collection(path, entries, allowed_themes):
    document = validate_collection(
        {"format": FORMAT, "version": VERSION, "layouts": entries}, allowed_themes,
    )
    raw = (json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False)
           + "\n").encode("utf-8")
    if len(raw) > MAX_COLLECTION_BYTES:
        raise ValueError("Collection is too large.")
    write_json_atomically(path, document)
