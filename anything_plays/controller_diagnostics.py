"""Privacy-conscious 3.1 controller diagnostic for support and QA.

The source report is a snapshot, not a recording or telemetry upload.
Never include ROM paths, camera images, account names, machine hostname,
user filesystem paths, or arbitrary Bluetooth device names.
"""
from __future__ import annotations

import platform
import sys

from anything_plays.build_identity import current_identity
from anything_plays.gamepad import SOURCES, mapped_buttons
from anything_plays.system_profiles import BUTTONS_BY_SYSTEM


def make_controller_report(
    reader, *, system, mappings=None, enabled=False, focused=False,
    emulator_running=False, camera_armed=False,
):
    """Describe one local controller state without accessing the filesystem.

    Reading pygame version and the raw *known* SDL control names is safe.
    A spoofed controller/device name and unrestricted settings are deliberately
    not serialized. Reports cannot certify a physical device was accepted.
    """
    if system not in BUTTONS_BY_SYSTEM:
        raise ValueError("Cannot report controller state for unknown console")
    raw = getattr(reader, "physical_buttons", frozenset())
    if not isinstance(raw, (set, frozenset, tuple, list)):
        raw = ()
    allowed = set(SOURCES)
    physical = tuple(item for item in SOURCES if item in allowed and item in raw)
    mapped = mapped_buttons(system, physical, mappings)
    pg = getattr(reader, "pygame", None)
    pygame_version = None
    sdl_version = None
    if pg is not None:
        version = getattr(getattr(pg, "version", None), "ver", None)
        if isinstance(version, str) and len(version) < 40:
            pygame_version = version
        try:
            reported_sdl = pg.get_sdl_version()
            if (isinstance(reported_sdl, (tuple, list))
                    and len(reported_sdl) == 3
                    and all(isinstance(n, int) and 0 <= n <= 99999
                            for n in reported_sdl)):
                sdl_version = ".".join(map(str, reported_sdl))
        except (AttributeError, RuntimeError, ValueError, OSError):
            pass
    identity = current_identity()
    return {
        "schema_version": 1,
        "status": "LOCAL_3_1_CONTROLLER_DIAGNOSTIC_NOT_RELEASE_ACCEPTANCE",
        "app_version": identity["version"],
        "app_channel": identity["channel"],
        "operating_system": platform.system(),
        "architecture": platform.machine(),
        "python_runtime": f"{sys.version_info.major}.{sys.version_info.minor}",
        "pygame_ce_version": pygame_version,
        "sdl_version": sdl_version,
        "selected_console": system,
        "controller_enabled": enabled is True,
        "controller_handle_present": (
            getattr(reader, "controller", None) is not None
        ),
        "focused": focused is True,
        "embedded_emulator_running": emulator_running is True,
        "camera_tracking_armed": camera_armed is True,
        "physical_inputs_detected": list(physical),
        "mapped_emulator_buttons": sorted(mapped),
        "controller_name_redacted": True,
        "rom_names_or_paths_included": False,
        "camera_images_included": False,
        "personal_identifiers_included": False,
        "physical_device_acceptance_verified": False,
        "redistribution_approved": False,
    }
