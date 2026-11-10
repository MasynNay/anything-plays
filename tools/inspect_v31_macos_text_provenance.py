"""Read-only executable section comparison: signed RC1 Mach-O vs official pygame wheel.

The observed identical __TEXT,__text bytes can identify the immediate wheel
binary family even after PyInstaller thins/signs a macOS executable. It does
NOT prove corresponding source, license compliance or user relinking ability.
Never rewrite either native binary, mount the RC DMG writable, or assert a
source correspondence approval from section equality alone.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

from tools.macho_wheel_slices import THIN, FAT, CPUS
from tools.prepare_v31_sdl_source_review import (
    EXPECTED_RECEIPT_STATUS, MAX_WHEEL_BYTES, RC_APP_COMMIT, WHEELS,
)

ARCHES = {"macos-arm64": "arm64", "macos-x64": "x86_64"}
EXPECTED_NATIVE_COUNT = {"macos-arm64": 121, "macos-x64": 120}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_NATIVE_BYTES = 60 * 1024 * 1024
MAX_TEXT_BYTES = 32 * 1024 * 1024
MAX_COMMAND_BYTES = 1 * 1024 * 1024
MACHO_SEGMENT_64 = 0x19
MACHO_HEADER_SIZE = 32
SECTION_64_SIZE = 80
SEGMENT_64_SIZE = 72


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def thin_slice(source, architecture):
    """Extract selected 64-bit Mach-O bytes without rewriting source.

    All offsets and overlap conditions are validated before accepting any
    purported universal slice; malformed binaries are rejected.
    """
    if not isinstance(source, bytes) or len(source) < MACHO_HEADER_SIZE:
        return None
    magic = source[:4]
    if magic in THIN:
        endian = THIN[magic]
        if struct.unpack_from(endian + "I", source, 4)[0] not in CPUS:
            return None
        detected = CPUS[struct.unpack_from(endian + "I", source, 4)[0]]
        return source if detected == architecture else None
    if magic not in FAT:
        return None
    endian, is64 = FAT[magic]
    count = struct.unpack_from(endian + "I", source, 4)[0]
    if not 1 <= count <= 16:
        raise ValueError("Impossible universal binary architecture count")
    fmt = endian + ("IIQQII" if is64 else "IIIII")
    item_size = struct.calcsize(fmt)
    header_end = 8 + count * item_size
    if header_end > len(source):
        raise ValueError("Truncated universal Mach-O header")
    slices = []
    selected = None
    for index in range(count):
        cpu, subtype, offset, size, *_ = struct.unpack_from(
            fmt, source, 8 + index * item_size)
        if not (header_end <= offset and size >= MACHO_HEADER_SIZE
                and offset + size <= len(source)):
            raise ValueError("Mach-O architecture exceeds wheel member")
        if any(offset < end and start < offset + size for start, end in slices):
            raise ValueError("Overlapping Mach-O architecture bytes")
        slices.append((offset, offset + size))
        if CPUS.get(cpu) == architecture:
            if selected is not None:
                raise ValueError("Duplicate matching Mach-O architecture")
            selected = source[offset:offset + size]
    return selected


def executable_text_fingerprint(source, architecture):
    """Hash actual __TEXT,__text section, not signatures or loader commands.

    This is strictly a section-byte comparison; an equal result neither
    verifies the whole file nor identifies the originating C source tree.
    """
    thin = thin_slice(source, architecture)
    if thin is None:
        return None
    magic = thin[:4]
    if magic not in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
        return None  # 32-bit or malformed Mach-O is not valid 3.1 evidence.
    endian = THIN[magic]
    cpu = struct.unpack_from(endian + "I", thin, 4)[0]
    if CPUS.get(cpu) != architecture:
        raise ValueError("Unexpected sliced Mach-O CPU type")
    ncmds, commands_size = struct.unpack_from(endian + "II", thin, 16)
    end = MACHO_HEADER_SIZE + commands_size
    if not (1 <= ncmds <= 2048 and 0 < commands_size <= MAX_COMMAND_BYTES
            and end <= len(thin)):
        raise ValueError("Invalid or truncated Mach-O commands")
    cursor = MACHO_HEADER_SIZE
    texts = []
    for _ in range(ncmds):
        if cursor + 8 > end:
            raise ValueError("Truncated Mach-O load command")
        command, size = struct.unpack_from(endian + "II", thin, cursor)
        if size < 8 or cursor + size > end:
            raise ValueError("Invalid Mach-O load command bounds")
        if command == MACHO_SEGMENT_64:
            if size < SEGMENT_64_SIZE:
                raise ValueError("Incomplete Mach-O segment")
            nsects = struct.unpack_from(endian + "I", thin, cursor + 64)[0]
            if size < SEGMENT_64_SIZE + nsects * SECTION_64_SIZE:
                raise ValueError("Incomplete Mach-O section table")
            for index in range(nsects):
                at = cursor + SEGMENT_64_SIZE + index * SECTION_64_SIZE
                sectname = thin[at:at + 16].split(b"\0", 1)[0]
                segname = thin[at + 16:at + 32].split(b"\0", 1)[0]
                if segname != b"__TEXT" or sectname != b"__text":
                    continue
                length = struct.unpack_from(endian + "Q", thin, at + 40)[0]
                offset = struct.unpack_from(endian + "I", thin, at + 48)[0]
                if (length <= 0 or length > MAX_TEXT_BYTES
                        or offset < end or offset + length > len(thin)):
                    raise ValueError("Unsafe Mach-O __TEXT,__text section")
                texts.append({
                    "size": length,
                    "sha256": sha256_bytes(thin[offset:offset + length]),
                })
        cursor += size
    if cursor != end:
        raise ValueError("Mach-O load commands length mismatch")
    if len(texts) > 1:
        raise ValueError("Ambiguous multiple executable __text sections")
    return texts[0] if texts else None


def build_wheel_index(wheel, target):
    """Require original official wheel bytes, and index native text only."""
    if target not in ARCHES:
        raise ValueError("Unknown target")
    wheel = Path(wheel)
    expected_filename, expected_sha = WHEELS[target]
    if (wheel.name != expected_filename or not wheel.is_file()
            or wheel.is_symlink()
            or not 1_000_000 <= wheel.stat().st_size <= MAX_WHEEL_BYTES
            or sha256_file(wheel) != expected_sha):
        raise ValueError("Official pinned pygame-ce wheel missing or altered")
    indexed = defaultdict(list)
    files_scanned = 0
    with zipfile.ZipFile(wheel) as archive:
        seen = set()
        for member in archive.infolist():
            name = member.filename
            if (name in seen or name.startswith("/") or "\\" in name
                    or ".." in name.split("/")
                    or member.file_size > MAX_NATIVE_BYTES):
                raise ValueError("Unsafe, duplicate or oversized wheel path")
            seen.add(name)
            if not name.lower().endswith((".so", ".dylib", ".pyd", ".dll")):
                continue
            if member.file_size < 64:
                continue
            fingerprint = executable_text_fingerprint(
                archive.read(member), ARCHES[target])
            if fingerprint:
                indexed[(fingerprint["size"], fingerprint["sha256"])].append(name)
                files_scanned += 1
    if files_scanned < 5:
        raise ValueError("Pygame wheel has unexpectedly few native text sections")
    return dict(indexed), files_scanned


def audit_bundle(bundle, installer, receipt, runtime_audit, wheel, target):
    if target not in ARCHES:
        raise ValueError("Unknown 3.1 target")
    bundle, installer = Path(bundle), Path(installer)
    if (not bundle.is_dir() or bundle.is_symlink()
            or not installer.is_file() or installer.is_symlink()):
        raise ValueError("Missing genuine mounted original 3.1 RC1 package")
    if (receipt.get("status") != EXPECTED_RECEIPT_STATUS[target]
            or receipt.get("target") != target
            or receipt.get("source_preview_revision") != RC_APP_COMMIT
            or receipt.get("native_core_count") != 11
            or receipt.get("console_profiles") != 18
            or receipt.get("installer") != installer.name
            or receipt.get("sha256") != sha256_file(installer)
            or receipt.get("public_release_approved") is not False
            or receipt.get("final_release_approved") is not False):
        raise ValueError("Wrong original RC1 installer provenance")
    if (runtime_audit.get("target") != target
            or runtime_audit.get("status") != "UNRELEASED_3_1_SDL_RUNTIME_INVENTORY"
            or runtime_audit.get("pygame_version") != "2.5.8"
            or runtime_audit.get("pygame_distribution") != "pygame-ce"
            or runtime_audit.get("redistribution_approved") is not False
            or runtime_audit.get("lgpl_relinking_reviewed") is not False):
        raise ValueError("Unreviewed native SDL runtime inventory")
    natives = runtime_audit.get("native_candidates")
    if (not isinstance(natives, list)
            or len(natives) != EXPECTED_NATIVE_COUNT[target]):
        raise ValueError("Wrong number of independently audited native files")
    index, official_count = build_wheel_index(wheel, target)
    rows, matches = [], 0
    root = bundle.resolve()
    visited = set()
    for native in natives:
        if not isinstance(native, dict):
            raise ValueError("Malformed installed native record")
        relative, expected_hash = native.get("path"), native.get("sha256")
        if (not isinstance(relative, str) or not relative
                or relative.startswith("/") or "\\" in relative
                or any(x in (".", "..", "") for x in relative.split("/"))
                or relative in visited or not isinstance(expected_hash, str)
                or not SHA256.fullmatch(expected_hash)):
            raise ValueError("Unsafe installed native path or digest")
        visited.add(relative)
        actual = bundle / relative
        if (actual.is_symlink() or not actual.is_file()
                or not actual.resolve().is_relative_to(root)
                or not 1 <= actual.stat().st_size <= MAX_NATIVE_BYTES
                or sha256_file(actual) != expected_hash):
            raise ValueError("Installed native file differs from frozen RC1 audit")
        fingerprint = executable_text_fingerprint(
            actual.read_bytes(), ARCHES[target])
        row = {"path": relative, "sha256": expected_hash}
        if fingerprint:
            row["text_section"] = fingerprint
            found = index.get((fingerprint["size"], fingerprint["sha256"]), [])
            row["upstream_matching_wheel_members"] = sorted(found)
            if found:
                matches += 1
        else:
            row["text_section"] = None
            row["upstream_matching_wheel_members"] = []
        rows.append(row)
    return {
        "schema_version": 1,
        "status": "PUBLIC_RC1_READ_ONLY_MACOS_TEXT_SECTION_AUDIT",
        "source_app_commit": RC_APP_COMMIT,
        "target": target,
        "installer": installer.name,
        "installer_sha256": sha256_file(installer),
        "official_wheel": wheel.name,
        "official_wheel_sha256": WHEELS[target][1],
        "published_wheel_native_sections": official_count,
        "installed_frozen_native_files_audited": len(rows),
        "exact_executable_text_section_matches": matches,
        "unmatched_installed_native_sections": len(rows) - matches,
        "native_file_evidence": rows,
        "interpretation": "Identical machine-code section bytes only, NOT proof of complete original binaries or sources",
        "wheel_build_source_provenance_verified": False,
        "native_corresponding_source_complete": False,
        "lgpl_library_replacement_verified": False,
        "redistribution_approved": False,
        "stable_3_1_release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--target", choices=sorted(ARCHES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text("utf-8"))
    audit = json.loads(args.audit.read_text("utf-8"))
    record = audit_bundle(args.bundle, args.installer, receipt, audit, args.wheel, args.target)
    dest = args.output.resolve()
    if dest.is_relative_to(args.bundle.resolve()):
        parser.error("Never write audit outputs into the original mounted RC1")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(record, indent=2) + "\n", "utf-8")
    print("Pinned signed", args.target, "frozen files:",
          record["installed_frozen_native_files_audited"],
          "section-identical upstream wheel files:",
          record["exact_executable_text_section_matches"],
          "NOT a stable release or LGPL approval")


if __name__ == "__main__":
    main()
