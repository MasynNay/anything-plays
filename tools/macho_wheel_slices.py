"""Decode universal macOS Mach-O slices for original wheel-byte comparison.

Pure byte parsing: no Mach-O rewriting or codesign removal. A matching
architecture slice is an exact byte match. A mismatch remains unresolved,
including when Apple's signing or PyInstaller alters the load commands.
"""
from __future__ import annotations

import hashlib
import struct

CPUS = {0x01000007: "x86_64", 0x0100000C: "arm64"}
# Header byte order is explicit because FAT and thin Mach-O may differ.
FAT = {b"\xca\xfe\xba\xbe": (">", False),
       b"\xbe\xba\xfe\xca": ("<", False),
       b"\xca\xfe\xba\xbf": (">", True),
       b"\xbf\xba\xfe\xca": ("<", True)}
THIN = {b"\xfe\xed\xfa\xce": ">",
        b"\xce\xfa\xed\xfe": "<",
        b"\xfe\xed\xfa\xcf": ">",
        b"\xcf\xfa\xed\xfe": "<"}


def architecture_slices(data):
    """Return exact SHA-256s of supported architectures from wheel bytes.

    Invalid or overlapping Mach-O slice offsets fail closed. Non-Mach-O
    binaries return an empty map: not evidence of correspondence.
    """
    if not isinstance(data, bytes) or len(data) < 8:
        return {}
    if data[:4] in THIN:
        endian = THIN[data[:4]]
        cpu = struct.unpack_from(endian + "I", data, 4)[0]
        arch = CPUS.get(cpu)
        return {arch: hashlib.sha256(data).hexdigest()} if arch else {}
    marker = FAT.get(data[:4])
    if marker is None:
        return {}
    endian, is_64bit = marker
    count = struct.unpack_from(endian + "I", data, 4)[0]
    if count < 1 or count > 16:
        raise ValueError("Invalid or oversized universal Mach-O architecture count")
    fmt = endian + ("IIQQII" if is_64bit else "IIIII")
    length = struct.calcsize(fmt)
    header_end = 8 + length * count
    if header_end > len(data):
        raise ValueError("Incomplete universal Mach-O header")
    segments = []
    result = {}
    for index in range(count):
        fields = struct.unpack_from(fmt, data, 8 + index * length)
        cpu, _subtype, offset, size = fields[:4]
        if (size < 8 or offset < header_end
                or offset + size > len(data)):
            raise ValueError("Universal Mach-O slice outside the published wheel")
        for previous_start, previous_end in segments:
            if offset < previous_end and previous_start < offset + size:
                raise ValueError("Overlapping universal Mach-O architecture slices")
        segments.append((offset, offset + size))
        name = CPUS.get(cpu)
        if name:
            if name in result:
                raise ValueError("Duplicate supported universal Mach-O architecture")
            result[name] = hashlib.sha256(data[offset:offset + size]).hexdigest()
    return result
