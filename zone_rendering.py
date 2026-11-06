"""Draw camera control zones with consistent opacity, artwork, and labels.

The renderer is deliberately independent of Tkinter. It accepts a BGR frame
and returns a new BGR frame; camera tracking works on the untouched source.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from system_profiles import DISABLED_MAPPING


def render_zone_overlay(frame, zones, mapping, active, *, opacity, size, style, artwork=None, shuffle_enabled=True):
    # Render translucent zones and readable labels at native camera
    # resolution; scaling to the preview happens afterward.
    height, width = frame.shape[:2]
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
    overlay = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(overlay)
    opacity = max(75, min(100, int(opacity)))
    # The previous opacity*1.5 calculation exceeded 255 and saturated.
    # Map the user-facing 75–100 range to visibly distinct alpha levels.
    tint_alpha = round(25 + (opacity - 75) / 25 * 170)
    size = max(8, min(160, int(size)))
    font = None
    for font_name in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                      '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                      'C:/Windows/Fonts/arialbd.ttf'):
        try:
            font = ImageFont.truetype(font_name, size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    for name, (x1, y1, x2, y2) in zones.items():
        if name == 'Shuffle' and not shuffle_enabled:
            continue
        if name != 'Shuffle' and mapping.get(name, name) == DISABLED_MAPPING:
            continue
        box = (int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        chosen = name == active
        color = (75, 240, 150) if chosen else (90, 220, 245)
        if style == 'High contrast':
            # Only high contrast tints the camera image; Outline leaves it clear.
            draw.rectangle(box, fill=(*color, tint_alpha))
        if artwork is not None:
            art = artwork.copy()
            art.thumbnail((max(1, box[2]-box[0]-12), max(1, box[3]-box[1]-12)))
            px = box[0] + (box[2]-box[0]-art.width)//2
            py = box[1] + (box[3]-box[1]-art.height)//2
            # Keep imported artwork's own alpha; tint opacity controls zone fills.
            overlay.alpha_composite(art, (px, py))
        label_box = draw.textbbox((0, 0), name, font=font, stroke_width=1)
        tw = label_box[2] - label_box[0]
        th = label_box[3] - label_box[1]
        lx = min(max(0, box[0]+5), max(0, width-tw-12))
        ly = min(max(0, box[1]+5), max(0, height-th-12))
        if style != 'Minimal':
            draw.rounded_rectangle((lx, ly, lx+tw+12, ly+th+12), radius=5,
                                   fill=(3, 21, 30, 235))
        draw.text((lx+6, ly+6-label_box[1]), name, font=font,
                  fill=(255, 255, 255, 255), stroke_width=1,
                  stroke_fill=(0, 0, 0, 255))
        # Draw the four-sided border LAST, on top of artwork and labels.
        # Keep the entire stroke inside the image, even for edge zones.
        stroke = 7 if chosen else (3 if style != 'Minimal' else 0)
        inset = (stroke + 1) // 2 + 1
        left = max(inset, min(width - inset - 1, box[0] + inset))
        top = max(inset, min(height - inset - 1, box[1] + inset))
        right = min(width - inset - 1, max(left + 1, box[2] - inset - 1))
        bottom = min(height - inset - 1, max(top + 1, box[3] - inset - 1))
        if stroke and right > left and bottom > top:
            draw.rectangle((left, top, right, bottom),
                           outline=(40, 255, 105, 255) if chosen else (90, 220, 245, 255),
                           width=stroke)
    rgba = Image.alpha_composite(rgba, overlay)
    return cv2.cvtColor(np.asarray(rgba.convert('RGB')), cv2.COLOR_RGB2BGR)
