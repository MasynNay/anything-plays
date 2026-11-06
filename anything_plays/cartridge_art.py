"""Generate locally drawn console cartridges with transparent backgrounds.

Cover art is loaded from the user's ROM directory; nothing is downloaded.
"""

from PIL import Image, ImageDraw, ImageFont, ImageOps


def cartridge_image(filename, system='gba', artwork_path=None):
    """Draw console-specific cartridges on a genuinely transparent canvas.

    All artwork is generated locally; no game cover art or network requests.
    The alpha channel remains transparent outside the plastic shell so tiles
    blend into every dark and light theme without a rectangular halo.
    """
    w, h = 300, 226
    image = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    system = system if system in ('gb', 'gbc', 'gba', 'snes') else 'gba'
    if system == 'gb':
        # Original Game Boy: tall, light gray cartridge with a corner notch.
        shell = [(80, 8), (219, 8), (229, 18), (229, 209), (72, 209), (72, 17)]
        d.polygon(shell, fill='#b8bcc0')
        d.line(shell + [shell[0]], fill='#656c72', width=4, joint='curve')
        d.rounded_rectangle((83, 22, 216, 43), radius=5, fill='#979da2')
        d.text((150, 33), 'GAME BOY', anchor='mm', fill='#333b44', font=cartridge_font(13, True))
        d.rounded_rectangle((87, 55, 213, 179), radius=5, fill='#f3f0e8', outline='#656c72', width=3)
        d.rectangle((87, 55, 213, 79), fill='#6d7380')
        d.text((150, 68), 'ANYTHING PLAYS', anchor='mm', fill='#ffffff', font=cartridge_font(10, True))
        label_box = (95, 85, 205, 170)
        ink = '#24344a'
        d.line((103, 196, 197, 196), fill='#84898e', width=3)
    elif system == 'gbc':
        # Color cartridge: translucent-purple style with tall silhouette.
        shell = [(79, 9), (220, 9), (230, 19), (230, 209), (70, 209), (70, 18)]
        d.polygon(shell, fill='#6c5b9b')
        d.line(shell + [shell[0]], fill='#40375e', width=4, joint='curve')
        d.rounded_rectangle((82, 23, 217, 45), radius=6, fill='#8574b4')
        d.text((150, 34), 'GAME BOY COLOR', anchor='mm', fill='#f4edff', font=cartridge_font(11, True))
        d.rounded_rectangle((86, 56, 214, 180), radius=6, fill='#ece7fb', outline='#40375e', width=3)
        d.rectangle((86, 56, 214, 80), fill='#4c75b5')
        d.text((150, 68), 'ANYTHING PLAYS', anchor='mm', fill='#ffffff', font=cartridge_font(10, True))
        label_box = (95, 86, 205, 171)
        ink = '#352c55'
        d.line((103, 197, 197, 197), fill='#9c8ec0', width=3)
    elif system == 'snes':
        # North American SNES cartridge: broad rectangular shell, softly
        # rounded upper shoulders, distinctive recessed label and side grips.
        # Draw at high resolution so downscaled tiles retain crisp edges.
        shell = [(37, 18), (263, 18), (275, 24), (282, 39),
                 (282, 196), (274, 206), (26, 206), (18, 196),
                 (18, 39), (25, 24)]
        d.polygon(shell, fill='#c9c8d0')
        d.line(shell + [shell[0]], fill='#696975', width=4, joint='curve')
        # Molded top ridge and stepped shoulder detail.
        d.rounded_rectangle((37, 24, 263, 48), radius=7, fill='#d9d8df', outline='#9b9aa6', width=2)
        d.line((28, 50, 272, 50), fill='#a2a1ad', width=3)
        # Vertical molded grip rails on the left and right.
        d.rounded_rectangle((25, 61, 44, 181), radius=6, fill='#b0afb9', outline='#8a8995', width=2)
        d.rounded_rectangle((256, 61, 275, 181), radius=6, fill='#b0afb9', outline='#8a8995', width=2)
        for x in (31, 37, 263, 269):
            d.line((x, 76, x, 167), fill='#d0cfd7' if x in (31, 263) else '#92919d', width=2)
        # A large rectangular paper label with a thin inset frame.
        d.rounded_rectangle((51, 57, 249, 175), radius=5, fill='#777581', outline='#5f5e6b', width=3)
        d.rounded_rectangle((56, 62, 244, 170), radius=3, fill='#f1eff0', outline='#d7d4d9', width=2)
        d.rectangle((58, 64, 242, 87), fill='#353b59')
        d.text((150, 75), 'SUPER NINTENDO', anchor='mm', fill='#ffffff', font=cartridge_font(12, True))
        d.rectangle((58, 88, 242, 92), fill='#8176ae')
        label_box = (65, 98, 235, 161)
        ink = '#27273b'
        # Bottom molded seam and central locking notch.
        d.line((45, 187, 255, 187), fill='#9695a0', width=3)
        d.rounded_rectangle((123, 194, 177, 205), radius=3, fill='#aaa9b4', outline='#777683', width=2)
    else:
        # Compact Game Boy Advance cartridge, with alpha outside the shell.
        d.rounded_rectangle((10, 14, 290, 212), radius=17, fill='#333a46', outline='#657080', width=3)
        d.rounded_rectangle((10, 14, 290, 46), radius=13, fill='#4b5563', outline='#737d8a', width=2)
        d.rectangle((22, 40, 278, 48), fill='#333a46')
        d.text((150, 30), 'GAME BOY ADVANCE', anchor='mm', fill='#d5dce7', font=cartridge_font(13, True))
        d.rounded_rectangle((39, 61, 261, 184), radius=9, fill='#10243e', outline='#8c98a8', width=3)
        d.rounded_rectangle((46, 68, 254, 177), radius=5, fill='#1e5182')
        d.polygon([(46, 68), (254, 68), (254, 89), (46, 141)], fill='#2e699d')
        d.text((150, 95), 'ANYTHING PLAYS', anchor='mm', fill='#d8e9ff', font=cartridge_font(11, True))
        label_box = (54, 113, 246, 169)
        ink = '#ffffff'
        d.line((112, 200, 188, 200), fill='#1a202b', width=4)

    # Optional game-specific artwork: place cover.png, cover.jpg, or an image
    # with the same filename stem alongside the ROM. No network required.
    if artwork_path is not None:
        try:
            with Image.open(artwork_path) as source:
                cover = source.convert('RGB')
            box_w = label_box[2] - label_box[0]
            box_h = label_box[3] - label_box[1]
            from PIL import ImageOps
            cover = ImageOps.fit(cover, (box_w, box_h), method=Image.Resampling.LANCZOS)
            image.paste(cover, (label_box[0], label_box[1]))
            return image
        except (OSError, ValueError):
            pass
    max_width = label_box[2] - label_box[0] - 6
    max_lines = 3 if system in ('gb', 'gbc') else 2
    font_size = 14 if system in ('gb', 'gbc') else 16
    font = cartridge_font(font_size, bold=True)
    words = filename.replace('_', ' ').split()
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if current and d.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [' '.join(lines[max_lines - 1:])]
    line_height = font_size + 4
    top = (label_box[1] + label_box[3] - line_height * len(lines)) // 2 + line_height // 2
    for index, line in enumerate(lines):
        while len(line) > 2 and d.textbbox((0, 0), line, font=font)[2] > max_width:
            line = line[:-2] + '…'
        d.text((150, top + index * line_height), line, anchor='mm', fill=ink, font=font)
    return image


def cartridge_font(size, bold=False):
    paths = (['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
              'C:/Windows/Fonts/arialbd.ttf'] if bold else
             ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
              '/System/Library/Fonts/Supplemental/Arial.ttf',
              'C:/Windows/Fonts/arial.ttf'])
    for path in paths:
        try: return ImageFont.truetype(path, size)
        except OSError: pass
    return ImageFont.load_default()
