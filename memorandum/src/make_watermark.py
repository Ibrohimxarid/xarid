# Builds the centre-of-page watermark: two logo slots side by side, faded.
# Usage: python3 make_watermark.py [museum_logo.png] [panshi_logo.png]
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1800, 760
SLOT_W, SLOT_H = 760, 600
ALPHA = 0.18  # watermark strength
GREY = (110, 110, 110)

def font(size, bold=False):
    p = "/usr/share/fonts/truetype/liberation/LiberationSerif-%s.ttf" % ("Bold" if bold else "Regular")
    return ImageFont.truetype(p, size)

def placeholder(label):
    im = Image.new("RGBA", (SLOT_W, SLOT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # dashed rounded frame
    x0, y0, x1, y1 = 8, 8, SLOT_W - 8, SLOT_H - 8
    d.rounded_rectangle((x0, y0, x1, y1), radius=40, outline=GREY + (255,), width=6)
    f1, f2 = font(150, True), font(64)
    for text, f, y in (("LOGO", f1, SLOT_H / 2 - 70), (label, f2, SLOT_H / 2 + 90)):
        w = d.textlength(text, font=f)
        d.text(((SLOT_W - w) / 2, y - f.size / 2), text, font=f, fill=GREY + (255,))
    return im

def fit(path):
    im = Image.open(path).convert("RGBA")
    im.thumbnail((SLOT_W, SLOT_H), Image.LANCZOS)
    return im

slots = [
    fit(sys.argv[1]) if len(sys.argv) > 1 else placeholder("[MUSEUM]"),
    fit(sys.argv[2]) if len(sys.argv) > 2 else placeholder("PANSHI"),
]

canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
centres = (W / 4 - 20, 3 * W / 4 + 20)
for im, cx in zip(slots, centres):
    canvas.alpha_composite(im, (int(cx - im.width / 2), int((H - im.height) / 2)))
# thin divider between the two logos
d = ImageDraw.Draw(canvas)
d.line((W / 2, H * 0.2, W / 2, H * 0.8), fill=GREY + (255,), width=5)

# fade the whole thing
r, g, b, a = canvas.split()
canvas = Image.merge("RGBA", (r, g, b, a.point(lambda v: int(v * ALPHA))))
canvas.save("watermark.png")
print("watermark.png", canvas.size)
