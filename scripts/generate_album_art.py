"""Album covers for The Quiet Hours and Sign-Off. Generative, minimal,
modern: a graded colour field, a single luminous element, fine film
grain, and quiet letter-spaced typography. No clip-art, no neon cliche.

The Quiet Hours: a nocturnal indigo field with a warm horizon glow low
in the frame -- light under a distant door. Literary serif.

Sign-Off: a near-black CRT field, faint scanlines, and the single white
dot of a television powering off, dead centre. Broadcast sans.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SZ = 2400
TRACKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Tracks")
FONTS = "/System/Library/Fonts/"


def vgrad(stops):
    """Vertical gradient. stops: list of (pos0-1, (r,g,b) 0-1)."""
    ys = np.linspace(0, 1, SZ)
    pos = [s[0] for s in stops]
    img = np.zeros((SZ, SZ, 3), np.float32)
    for c in range(3):
        col = np.interp(ys, pos, [s[1][c] for s in stops])
        img[:, :, c] = col[:, None]
    return img


def glow(img, cx, cy, radius, color, intensity, aspect=1.0):
    yy, xx = np.mgrid[0:SZ, 0:SZ].astype(np.float32)
    d = np.sqrt(((xx - cx * SZ) / aspect) ** 2 + (yy - cy * SZ) ** 2) / (radius * SZ)
    falloff = np.exp(-(d ** 2) * 2.2) * intensity
    for c in range(3):
        img[:, :, c] += falloff * color[c]
    return img


def grain(img, amount, rng):
    n = rng.standard_normal((SZ, SZ, 1)).astype(np.float32)
    # slight luma-coupled grain: stronger in midtones
    luma = img.mean(axis=2, keepdims=True)
    weight = 0.5 + 0.5 * (1 - np.abs(luma - 0.4) * 2).clip(0, 1)
    return img + n * amount * weight


def vignette(img, strength):
    yy, xx = np.mgrid[0:SZ, 0:SZ].astype(np.float32)
    d = np.sqrt((xx - SZ / 2) ** 2 + (yy - SZ / 2) ** 2) / (SZ * 0.72)
    v = 1 - (d ** 2.4) * strength
    return img * v.clip(0, 1)[:, :, None]


def scanlines(img, strength):
    lines = np.ones(SZ, np.float32)
    lines[::3] = 1 - strength
    return img * lines[:, None, None]


def font(path, idx, size):
    return ImageFont.truetype(os.path.join(FONTS, path), size, index=idx)


def tracked_text(draw, cy, text, fnt, color, tracking, cx=0.5):
    widths = [draw.textbbox((0, 0), ch, font=fnt)[2] for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx * SZ - total / 2
    asc, desc = fnt.getmetrics()
    y = cy * SZ - (asc + desc) / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=color)
        x += w + tracking


def finish(img, path):
    out = (img.clip(0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(out, "RGB")
    im.save(path + ".png")
    im.save(path + ".jpg", quality=92)
    print("wrote", os.path.basename(path) + ".png/.jpg")


# ---- The Quiet Hours ---------------------------------------------------------

def quiet_hours():
    rng = np.random.default_rng(7)
    img = vgrad([(0.0, (0.055, 0.065, 0.10)),
                 (0.42, (0.085, 0.10, 0.145)),
                 (0.72, (0.13, 0.12, 0.14)),
                 (1.0, (0.22, 0.155, 0.12))])
    img = glow(img, 0.5, 0.80, 0.55, (0.95, 0.72, 0.45), 0.16)   # warm horizon
    img = glow(img, 0.5, 0.80, 1.1, (0.6, 0.45, 0.35), 0.06)
    img = glow(img, 0.30, 0.16, 0.5, (0.35, 0.42, 0.60), 0.04)   # cool depth, top
    img = grain(img, 0.018, rng)
    img = vignette(img, 0.42)

    im = (img.clip(0, 1) * 255).astype(np.uint8)
    pim = Image.fromarray(im, "RGB")
    d = ImageDraw.Draw(pim)
    title = font("Optima.ttc", 0, 150)
    small = font("Optima.ttc", 0, 46)
    ink = (223, 216, 205)
    # thin hairline above the title
    y0 = 0.475
    d.line([(0.32 * SZ, y0 * SZ - 150), (0.68 * SZ, y0 * SZ - 150)], fill=(150, 140, 128), width=2)
    tracked_text(d, y0, "the quiet hours", title, ink, 14)
    tracked_text(d, 0.556, "T W E L V E   N O C T U R N E S", small, (170, 160, 148), 6)
    finish(np.asarray(pim).astype(np.float32) / 255, os.path.join(TRACKS_DIR, "The Quiet Hours", "cover"))


# ---- Sign-Off ----------------------------------------------------------------

def sign_off():
    rng = np.random.default_rng(3)
    img = vgrad([(0.0, (0.028, 0.028, 0.045)),
                 (0.5, (0.05, 0.042, 0.075)),
                 (1.0, (0.075, 0.055, 0.055))])
    # the power-off dot: bright small core + soft amber bloom, dead centre
    img = glow(img, 0.5, 0.455, 0.34, (0.55, 0.42, 0.30), 0.10)   # outer bloom
    img = glow(img, 0.5, 0.455, 0.10, (0.85, 0.72, 0.52), 0.30)   # inner bloom
    img = glow(img, 0.5, 0.455, 0.022, (1.0, 0.97, 0.90), 0.95)   # hot core
    img = grain(img, 0.032, rng)
    img = scanlines(img, 0.06)
    img = vignette(img, 0.62)

    im = (img.clip(0, 1) * 255).astype(np.uint8)
    pim = Image.fromarray(im, "RGB")
    d = ImageDraw.Draw(pim)
    title = font("HelveticaNeue.ttc", 0, 128)
    small = font("HelveticaNeue.ttc", 0, 40)
    ink = (198, 190, 178)
    tracked_text(d, 0.63, "SIGN-OFF", title, ink, 42)
    tracked_text(d, 0.70, "N I G H T   M U S I C   ·   M M L X X X I I I", small, (120, 112, 105), 4)
    finish(np.asarray(pim).astype(np.float32) / 255, os.path.join(TRACKS_DIR, "Sign-Off", "cover"))


if __name__ == "__main__":
    quiet_hours()
    sign_off()
    print("Album art complete.")
