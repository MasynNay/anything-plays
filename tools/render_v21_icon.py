"""Build 2.1's corrected native app icons from one reviewed source image.

The 2.0 assets are intentionally left alone. This source WebP is the
approved 2.1 drawing: the fish holds the plain *back* of its handheld,
without front-side buttons. Every platform uses the same source art.

Usage:
    python tools/render_v21_icon.py

The generated files live under build/v21-icon/, which is already temporary
build output. No files in assets/ or stable v2.0 are overwritten.
"""
from pathlib import Path
import sys

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "anything_plays_v21.webp"
OUTPUT = ROOT / "build" / "v21-icon"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def render(source=SOURCE, output=OUTPUT):
    source = Path(source)
    output = Path(output)
    if not source.is_file():
        raise FileNotFoundError(f"2.1 corrected icon source missing: {source}")

    with Image.open(source) as raw:
        raw.load()
        if raw.width != raw.height or min(raw.size) < 128:
            raise ValueError("The 2.1 app icon must be a square, high-res image")
        # Keep a single RGBA master so PNG/ICO/iconutil use matching artwork.
        image = raw.convert("RGBA")

    output.mkdir(parents=True, exist_ok=True)
    master = image.resize((1024, 1024), Image.Resampling.LANCZOS)
    # Native icns generation needs a 1024px source for 512@2x.
    icon_png = output / "anything_plays.png"
    master.save(icon_png, format="PNG", optimize=True)

    small_png = output / "anything_plays_small.png"
    image.resize((256, 256), Image.Resampling.LANCZOS).save(
        small_png, format="PNG", optimize=True
    )

    icon_ico = output / "anything_plays.ico"
    master.save(
        icon_ico, format="ICO", sizes=[(size, size) for size in ICO_SIZES]
    )
    return icon_png, small_png, icon_ico


if __name__ == "__main__":
    png, small, ico = render()
    print(f"Prepared 2.1 icon: {png}, {small}, {ico}", flush=True)
