"""Maakt uit het aangeleverde AO-online-logo (assets/ao-online-logo-origineel.jpg) de varianten voor de site.
Eenmalig draaien als het logo verandert; vraagt Pillow (pip install pillow). build_site.py heeft het niet nodig."""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, 'assets')
src = Image.open(os.path.join(A, 'ao-online-logo-origineel.jpg')).convert('RGB')


def transparant(im):
    """Wit buiten het logoblok (afgeronde hoeken) transparant maken, zodat het ook op donkere achtergrond klopt."""
    im = im.convert('RGBA')
    w, h = im.size
    marker = (255, 0, 255, 255)
    for p in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if sum(im.getpixel(p)[:3]) > 720:
            ImageDraw.floodfill(im, p, marker, thresh=60)
    px = im.load()
    for y in range(h):
        for x in range(w):
            if px[x, y] == marker:
                px[x, y] = (255, 255, 255, 0)
    return im


badge = transparant(src.crop((0, 0, src.width, 480)))       # 'AO online .nl' zonder ondertitel
badge.resize((round(badge.width * 96 / badge.height), 96), Image.LANCZOS).save(os.path.join(A, 'ao-online-logo.png'), optimize=True)
ao = transparant(src.crop((0, 0, 480, 480)))                 # oranje 'AO'-blok voor het tabbladicoon
ao.resize((64, 64), Image.LANCZOS).save(os.path.join(A, 'favicon.png'), optimize=True)
ao.resize((180, 180), Image.LANCZOS).convert('RGB').save(os.path.join(A, 'apple-touch-icon.png'), optimize=True)
print('klaar')
