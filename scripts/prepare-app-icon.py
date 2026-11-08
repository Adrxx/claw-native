"""Render local-only AppIcon assets. No network, reference execution or copied art in source.

The tracked fallback is an original compass, rendered with face(None) below.
Retail inputs and every resulting raster stay in ignored directories.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'App/GeneratedIcons.xcassets'


def portrait(data):
    path = data / 'MENU/STATES/MENU/IMAGES/CLAW/FRAME011.PID'
    palette_path = data / 'MENU/STATES/MENU/SCREENS/MENU.PCX'
    if not path.exists() or not palette_path.exists():
        return None, 'original compass fallback'
    raw = path.read_bytes()
    if len(raw) < 32:
        raise ValueError('Truncated icon sprite')
    _, flags, width, height = struct.unpack_from('<4I', raw)
    if not flags & 32 or not 0 < width <= 4096 or not 0 < height <= 4096:
        raise ValueError('Unsupported icon sprite')
    colors = list(raw[-768:]) if flags & 128 else Image.open(palette_path).getpalette()
    if colors is None or len(colors) != 768:
        raise ValueError('Missing icon palette')
    limit = len(raw) - (768 if flags & 128 else 0)
    rgba = bytearray(width * height * 4)
    position = 32
    for y in range(height):
        x = 0
        while x < width:
            if position >= limit:
                raise ValueError('Truncated icon raster')
            token = raw[position]
            position += 1
            count = token & 127
            if not count or x + count > width:
                raise ValueError('Invalid icon raster run')
            if token < 128:
                if position + count > limit:
                    raise ValueError('Truncated icon literal')
                for i, index in enumerate(raw[position:position + count]):
                    target = (y * width + x + i) * 4
                    rgba[target:target + 4] = bytes(colors[index * 3:index * 3 + 3] + [255])
                position += count
            x += count
    image = Image.frombytes('RGBA', (width, height), bytes(rgba))
    box = image.getbbox()
    if box is None:
        raise ValueError('Empty icon sprite')
    image = image.crop(box)
    # Front-facing menu pose: retain the hat, face and coat, ending at the belt.
    image = image.crop((0, 0, image.width, round(image.height * .64)))
    image = image.crop(image.getbbox())
    return image, {'sprite': str(path.relative_to(data)),
                   'sha256': hashlib.sha256(raw).hexdigest(),
                   'palette_sha256': hashlib.sha256(palette_path.read_bytes()).hexdigest()}


def face(art):
    size = 1024
    image = Image.new('RGB', (size, size))
    pixels = image.load()
    for y in range(size):
        for x in range(size):
            glow = max(0, 1 - math.hypot((x - 460) / 850, (y - 290) / 1000))
            pixels[x, y] = (int(8 + 14 * glow), int(17 + 33 * glow), int(35 + 46 * glow))
    image = image.convert('RGBA')
    draw = ImageDraw.Draw(image)
    # Engraved gold medallion, comfortably inside the system's corner mask.
    draw.ellipse((116, 116, 908, 908), outline='#987039', width=3)
    draw.ellipse((132, 132, 892, 892), outline='#d5ad61', width=8)
    draw.ellipse((149, 149, 875, 875), outline='#574a35', width=2)
    for a in range(0, 360, 30):
        angle = math.radians(a)
        points = [(512 + r * math.sin(angle), 512 - r * math.cos(angle)) for r in (365, 378)]
        draw.line(points, fill='#c09a56', width=3)
    if art is None:
        # Original geometry; no retail art is necessary to build the icon.
        for a in range(0, 360, 90):
            angle = math.radians(a)
            def p(x, y):
                return (512 + x * math.cos(angle) - y * math.sin(angle),
                        512 + x * math.sin(angle) + y * math.cos(angle))
            draw.polygon([p(0, -275), p(68, 0), p(0, 76)], fill='#f1d99b')
            draw.polygon([p(0, -275), p(-68, 0), p(0, 76)], fill='#a47c3d')
        draw.ellipse((478, 478, 546, 546), fill='#14283e', outline='#f1d99b', width=7)
    else:
        # Integer nearest-neighbour enlargement preserves the original pixel
        # clusters; one gentle final reduction avoids ringing around the face.
        factor = math.ceil(710 / max(art.size))
        art = art.resize((art.width * factor, art.height * factor), Image.Resampling.NEAREST)
        art.thumbnail((710, 710), Image.Resampling.LANCZOS)
        layer = Image.new('RGBA', image.size)
        layer.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2 + 12))
        alpha = layer.getchannel('A')
        rim = alpha.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(1))
        outline = Image.new('RGBA', image.size, '#d9ad58'); outline.putalpha(rim)
        shadow = Image.new('RGBA', image.size, '#020812'); shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(18)))
        image = Image.alpha_composite(image, shadow)
        image = Image.alpha_composite(image, outline)
        image = Image.alpha_composite(image, layer)
    return image.convert('RGB')


def mac_icon(flat):
    # Standard 824 px tile within a 1024 px transparent macOS canvas.
    mask = Image.new('L', (1024, 1024))
    ImageDraw.Draw(mask).rounded_rectangle((100, 100, 924, 924), radius=184, fill=255)
    shadow_mask = Image.new('L', mask.size)
    shadow_mask.paste(mask, (0, 16))
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(17)).point(lambda p: p * 80 // 255)
    image = Image.new('RGBA', mask.size, (0, 0, 0, 0))
    image.putalpha(shadow_mask)
    tile = Image.new('RGBA', mask.size)
    tile.paste(flat.resize((824, 824), Image.Resampling.LANCZOS), (100, 100))
    tile.putalpha(mask)
    return Image.alpha_composite(image, tile)


def write_content(path, content):
    # Two app sessions may prepare identical catalogs. Publish each file
    # atomically and leave unchanged inputs alone for incremental Xcode builds.
    if path.exists() and path.read_bytes() == content:
        return
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    temporary.write_bytes(content)
    temporary.replace(path)


def save_image(image, path):
    import io
    buffer = io.BytesIO(); image.save(buffer, format='PNG')
    write_content(path, buffer.getvalue())


def generate(data=ROOT / 'App/GameData', catalog=CATALOG, preview=ROOT / 'work/icon/preview.png'):
    art, provenance = portrait(data)
    flat = face(art) if art is not None else Image.open(ROOT / 'App/IconFallback.png').convert('RGB')
    mac = mac_icon(flat)
    target = catalog / 'AppIcon.appiconset'; target.mkdir(parents=True, exist_ok=True)
    entries = []
    for idiom, points, scales in [('ipad', 20, (1, 2)), ('ipad', 29, (1, 2)),
                                   ('ipad', 40, (1, 2)), ('ipad', 76, (1, 2)),
                                   ('ipad', 83.5, (2,)), ('ios-marketing', 1024, (1,))] + [
                                   ('mac', n, (1, 2)) for n in (16, 32, 128, 256, 512)]:
        for scale in scales:
            pixels = int(points * scale)
            name = f'{idiom}-{pixels}.png'
            save_image((mac if idiom == 'mac' else flat).resize((pixels, pixels), Image.Resampling.LANCZOS), target / name)
            entries.append(dict(idiom=idiom, size=f'{points}x{points}', scale=f'{scale}x', filename=name))
    write_content(target / 'Contents.json', (json.dumps(dict(images=entries, info=dict(author='xcode', version=1)), indent=2) + '\n').encode())
    write_content(catalog / 'Contents.json', b'{"info":{"author":"xcode","version":1}}\n')
    preview.parent.mkdir(parents=True, exist_ok=True)
    sizes = (16, 20, 29, 32, 40, 58, 64, 76, 80, 128, 152, 167, 256, 512, 1024)
    # One row per platform/background; large sizes retain a labelled 256 px
    # thumbnail, with the actual 512/1024 images alongside the preview sheet.
    sheet = Image.new('RGB', (32 + sum(max(min(n, 256), 29) + 12 for n in sizes), 1200))
    draw = ImageDraw.Draw(sheet)
    for row, (platform, source, bg, ink) in enumerate([
            ('iPad', flat, '#f2eee5', '#17283c'), ('iPad', flat, '#101722', '#eee5d0'),
            ('Mac', mac, '#f2eee5', '#17283c'), ('Mac', mac, '#101722', '#eee5d0')]):
        y = row * 300; draw.rectangle((0, y, sheet.width, y + 300), fill=bg)
        draw.text((16, y + 12), platform + ' / pixels (512 and 1024 shown at 256)', fill=ink)
        x = 16
        for n in sizes:
            actual = source.resize((n, n), Image.Resampling.LANCZOS)
            display = actual if n <= 256 else actual.resize((256, 256), Image.Resampling.LANCZOS)
            sheet.paste(display, (x, y + 34), display if display.mode == 'RGBA' else None)
            draw.text((x, y + 274), str(n), fill=ink)
            x += max(display.width, 29) + 12
    save_image(sheet, preview)
    result = dict(status='pass', source=provenance, catalog=str(catalog), preview=str(preview), slots=len(entries))
    (preview.parent / 'provenance.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'App/GameData')
    args = parser.parse_args()
    print(json.dumps(generate(data=args.data)))
