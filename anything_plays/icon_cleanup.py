"""Remove ONLY edge-connected dark matte around the existing 3.0 icon.

Preserve the approved betta/handheld illustration, border, colors and shape.
This is NOT a redesign: every original RGB pixel is kept unchanged.
The original WebP and stable 2.0 assets are never overwritten; package-time
PNG/ICO/ICNS as well as the Tk app icon use the same transparent treatment.
"""
from PIL import Image
import numpy as np
import cv2


def clean_icon_background(source):
    """Return a new RGBA image without the black matte outside its border.

    The matte is identified as an edge-connected, low-brightness component.
    Interior black details are preserved because they are *not* connected
    across the existing closed cyan border. No edge smoothing or shape
    changes are permitted; the only allowed change is exterior alpha.
    """
    rgba = np.array(source.convert("RGBA"), dtype=np.uint8, copy=True)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    height, width = alpha.shape
    if min(width, height) < 16:
        raise ValueError("Icon source is too small for safe matte removal")
    # Do not damage an already-transparent icon from a future art revision.
    if all(alpha[y, x] < 12 for y, x in (
            (0, 0), (0, width - 1),
            (height - 1, 0), (height - 1, width - 1))):
        return Image.fromarray(rgba, "RGBA")

    peak = np.max(rgb, axis=2)
    floor = np.min(rgb, axis=2)
    # Very dark, mostly-neutral exterior matte (true black/charcoal).
    # Do not mistake saturated blue/cyan highlights for background.
    candidates = (
        (peak <= 70)
        & ((peak - floor) <= 44)
        & (alpha >= 12)
    ).astype(np.uint8)
    count, labels = cv2.connectedComponents(candidates, connectivity=8)
    if count < 2:
        return Image.fromarray(rgba, "RGBA")

    # Only components physically connected to image borders can be matte.
    # A dark character outline or eye *inside* the neon shape is untouched.
    edge_labels = set(labels[0, :]) | set(labels[-1, :])
    edge_labels.update(labels[:, 0])
    edge_labels.update(labels[:, -1])
    edge_labels.discard(0)
    exterior = np.isin(labels, tuple(edge_labels))
    # Requiring at least a few pixels prevents erasing scattered black
    # ink touching a straight border on an already clean design.
    if np.count_nonzero(exterior) < max(16, width * height // 2000):
        return Image.fromarray(rgba, "RGBA")
    alpha[exterior] = 0

    # Strict preservation contract: DO NOT touch any pixel bordering the
    # illustration, its dark linework, eye, handheld, face, or cyan frame.
    # In particular, NEVER dilate/blur this mask: a 2px "fringe cleanup"
    # could visibly damage the original fish's dark outline.
    # RGB channels remain byte-for-byte IDENTICAL to the user's source.
    # Only fully connected exterior matte receives alpha=0.
    rgba[:, :, 3] = alpha
    return Image.fromarray(rgba, "RGBA")
