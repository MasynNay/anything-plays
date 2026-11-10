"""Create genuine README detail screenshots from the original packaged-app capture.

These are reproducible CROPS of the real 3.0 Linux/Tk screenshot, not
redrawn UI or synthetic game footage. Cropping is intentionally fixed so
small screenshots focus on meaningful controls rather than empty camera/ROM
content. The original full-size screenshot is retained unchanged.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "site/assets/anything-plays-desktop-preview.webp"
OUTPUT = ROOT / "docs/screenshots/current"
EXPECTED = (1342, 846)
CROPS = {
    "camera-controls.webp": (10, 128, 657, 815),
    "game-library-and-audio.webp": (676, 128, 1340, 815),
}


def generate(original: Path = ORIGINAL, output: Path = OUTPUT) -> list[Path]:
    """Preserve original pixels and produce two clearly attributed UI details."""
    if original.is_symlink() or not original.is_file():
        raise ValueError("Original actual packaged app screenshot is missing")
    with Image.open(original) as source:
        if source.format != "WEBP" or source.size != EXPECTED:
            raise ValueError(f"Unexpected source screenshot identity: {source.size}")
        source.load()
        output.mkdir(parents=True, exist_ok=True)
        result: list[Path] = []
        for name, region in CROPS.items():
            if region[0] < 0 or region[1] < 0 or region[2] > source.width or region[3] > source.height:
                raise ValueError("Screenshot crop extends outside the actual window")
            detail = source.crop(region).convert("RGB")
            if detail.width < 500 or detail.height < 500:
                raise ValueError("Screenshot crop lost the actual application UI")
            dest = output / name
            if dest.is_symlink():
                raise ValueError("Refusing symlinked screenshot output")
            detail.save(dest, format="WEBP", quality=90, method=6)
            with Image.open(dest) as check:
                if check.format != "WEBP" or check.size != detail.size:
                    raise ValueError("Corrupt screenshot crop: " + name)
            result.append(dest)
            print(f"Captured real app UI detail: {dest} ({detail.width}x{detail.height})")
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=ORIGINAL)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    result = generate(args.original, args.output)
    assert len(result) == 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
