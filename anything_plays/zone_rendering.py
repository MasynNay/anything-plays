"""Draw camera control zones with consistent opacity, artwork, and labels.

The renderer is deliberately independent of Tkinter. It accepts a BGR frame
and returns a new BGR frame; camera tracking works on the untouched source.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from anything_plays.system_profiles import DISABLED_MAPPING


def render_zone_overlay(frame, zones, mapping, active, *, opacity, size, style, artwork=None, shuffle_enabled=True, border_width=6, label_position='Center'):
    # Render translucent zones and readable labels at native camera
    # resolution; scaling to the preview happens afterward.
    height, width = frame.shape[:2]
    rgba = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
    overlay = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(overlay)
    opacity = max(75, min(100, int(opacity)))
    border_width = max(2, min(16, int(border_width)))
    label_position = label_position if label_position in ('Center', 'Top-left') else 'Center'
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
        if style in ('High contrast', 'Bold'):
            # Bold has a dark readable panel plus a vivid translucent fill.
            draw.rectangle(box, fill=(*color, max(100, tint_alpha) if style == 'Bold' else tint_alpha))
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
        if label_position == 'Center':
            lx = (box[0] + box[2] - tw - 20) // 2
            ly = (box[1] + box[3] - th - 18) // 2
        else:
            lx, ly = box[0] + 5, box[1] + 5
        lx = min(max(0, lx), max(0, width - tw - 20))
        ly = min(max(0, ly), max(0, height - th - 18))
        if style != 'Minimal':
            draw.rounded_rectangle((lx, ly, lx+tw+20, ly+th+18), radius=7,
                                   fill=(3, 16, 27, 242) if style == 'Bold' else (3, 21, 30, 225),
                                   outline=(246, 252, 255, 220) if style == 'Bold' else None,
                                   width=2)
        draw.text((lx+10, ly+9-label_box[1]), name, font=font,
                  fill=(255, 255, 255, 255), stroke_width=2 if style == 'Bold' else 1,
                  stroke_fill=(0, 0, 0, 255))
        # Draw the four-sided border LAST, on top of artwork and labels.
        # Keep the entire stroke inside the image, even for edge zones.
        stroke = min(20, border_width + 4) if chosen else (border_width if style != 'Minimal' else 0)
        inset = (stroke + 1) // 2 + 1
        left = max(inset, min(width - inset - 1, box[0] + inset))
        top = max(inset, min(height - inset - 1, box[1] + inset))
        right = min(width - inset - 1, max(left + 1, box[2] - inset - 1))
        bottom = min(height - inset - 1, max(top + 1, box[3] - inset - 1))
        if stroke and right > left and bottom > top:
            draw.rectangle((left, top, right, bottom),
                           outline=(48, 255, 121, 255) if chosen else (105, 241, 255, 255),
                           width=stroke)
    rgba = Image.alpha_composite(rgba, overlay)
    return cv2.cvtColor(np.asarray(rgba.convert('RGB')), cv2.COLOR_RGB2BGR)
