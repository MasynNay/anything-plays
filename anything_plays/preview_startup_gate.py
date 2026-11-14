"""Pure startup acceptance gate for a frozen, unreleased 3.2 preview.

Only a genuine embedded preview identity can pass. The source launcher
AP_V32_PREVIEW=1 is not sufficient to pass this packaged-binary QA gate.
No camera, controller, ROM, filesystem write, or network access is required.
"""

from anything_plays.build_identity import make_identity


def verify_preview_startup(app, root, *, identity, frozen):
    """Return whether an already-running Tk App is safely isolated.

    This is intentionally a cheap *read-only* predicate. Physical webcam,
    SDL controller, native gameplay and full-console coverage remain separate
    QA obligations.
    """
    expected = make_identity("v32_preview")
    reader = getattr(app, "_gamepad", None)
    prefs = getattr(app, "preferences_path", None)
    return bool(
        frozen
        and identity == expected
        and prefs is not None
        and prefs.parent.name == expected["settings_namespace"]
        and root.title() == expected["title"]
        and getattr(app, "cap", None) is None
        and reader is not None
        and getattr(reader, "api", None) is None
        and getattr(app, "armed", None) is False
    )
