#!/usr/bin/env python3
"""Draw the front page of Saturday 21 November 2026 as one image.

A pure-stdlib program: it rasterises a newspaper front page (masthead with
the date, six verified stories from 21 November 2026, simple pictograms)
into a 1024x1024 PNG and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output/entry.png). No network, no randomness, no time: two runs
write identical bytes.
"""

import hashlib
import math
import os
import struct
import zlib

W, H = 1024, 1024

# --- palette ---------------------------------------------------------------
PAPER = (245, 239, 224)      # newsprint cream
WHITE = (255, 255, 255)
INK = (26, 26, 26)           # headline ink
BODY = (58, 58, 58)          # summary ink
NAVY = (20, 33, 61)          # masthead
GOLD = (232, 184, 75)        # date line
CREAM = (247, 243, 232)      # masthead text
MUTED = (110, 105, 90)       # footer ink
RULE = (180, 172, 150)       # thin rules

# --- 5x7 bitmap font (uppercase, digits, punctuation) ----------------------
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
}


def text_width(text, scale):
    """Pixel width of text at the given scale (5 px glyph + 1 px gap)."""
    return len(text) * 6 * scale - scale


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# --- canvas ----------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.px[o], self.px[o + 1], self.px[o + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            o = self._off(x0, yy)
            row = bytes(color) * (x1 - x0)
            self.px[o:o + (x1 - x0) * 3] = row

    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)

    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)

    def line(self, x0, y0, x1, y1, color):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline(cx - dx, cy + dy, 2 * dx + 1, color)

    def ring(self, cx, cy, r, t, color):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            inner = int(math.sqrt(max(0, (r - t) * (r - t) - dy * dy))) if abs(dy) < r - t else 0
            self.hline(cx - dx, cy + dy, dx - inner, color)
            self.hline(cx + inner, cy + dy, dx - inner, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for dy in range(-ry, ry + 1):
            dx = int(rx * math.sqrt(max(0.0, 1.0 - (dy * dy) / (ry * ry))))
            self.hline(cx - dx, cy + dy, 2 * dx + 1, color)

    def polygon(self, points, color):
        """Scanline fill of a simple polygon."""
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(xs[i]), y, max(1, int(xs[i + 1]) - int(xs[i])), color)

    def star(self, cx, cy, r_out, r_in, color):
        pts = []
        for i in range(10):
            r = r_out if i % 2 == 0 else r_in
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
        self.polygon(pts, color)

    def text(self, x, y, s, scale, color):
        for ch in s:
            glyph = FONT.get(ch)
            if glyph is None:
                x += 6 * scale
                continue
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(x + col * scale, y + row * scale, scale, scale, color)
            x += 6 * scale

    def text_center(self, cx, y, s, scale, color):
        self.text(cx - text_width(s, scale) // 2, y, s, scale, color)


# --- pictograms (drawn in a 120x120 box at x, y) ---------------------------
def draw_ship(c, x, y, col):
    # two drones above
    for dx, dy in ((18, 8), (92, 4)):
        c.circle(x + dx, y + dy, 4, col)
        c.hline(x + dx - 9, y + dy - 6, 18, col)
        c.hline(x + dx - 9, y + dy + 6, 18, col)
    # hull + deck + containers + mast
    c.polygon([(x + 8, y + 62), (x + 112, y + 62), (x + 100, y + 92), (x + 20, y + 92)], col)
    c.fill_rect(x + 22, y + 40, 26, 22, col)
    c.fill_rect(x + 52, y + 34, 26, 28, col)
    c.fill_rect(x + 82, y + 44, 20, 18, col)
    c.vline(x + 60, y + 14, 26, col)
    c.fill_rect(x + 60, y + 14, 14, 8, GOLD)
    # waves
    for wy in (y + 100, y + 108):
        for k in range(6):
            c.hline(x + k * 20, wy, 12, col)


def draw_crowd(c, x, y, col):
    # heads and shoulders, two placards
    for hx in (16, 44, 72, 100):
        c.circle(x + hx, y + 58, 11, col)
        c.fill_rect(x + hx - 10, y + 72, 20, 22, col)
    c.fill_rect(x + 30, y + 14, 4, 28, col)
    c.fill_rect(x + 12, y + 2, 40, 12, GOLD)
    c.fill_rect(x + 84, y + 24, 4, 22, col)
    c.fill_rect(x + 68, y + 12, 36, 12, col)


def draw_badge(c, x, y, col):
    c.ring(x + 60, y + 52, 40, 5, col)
    c.star(x + 60, y + 52, 30, 13, col)
    c.polygon([(x + 44, y + 88), (x + 76, y + 88), (x + 70, y + 112), (x + 50, y + 112)], GOLD)
    c.circle(x + 60, y + 100, 5, col)


def draw_truck(c, x, y, col):
    # aid truck: cargo box with cross, cab, wheels
    c.fill_rect(x + 10, y + 34, 62, 44, col)
    c.fill_rect(x + 76, y + 48, 30, 30, col)
    c.fill_rect(x + 82, y + 54, 16, 12, WHITE)
    c.fill_rect(x + 36, y + 42, 8, 24, WHITE)
    c.fill_rect(x + 28, y + 50, 24, 8, WHITE)
    c.circle(x + 30, y + 84, 10, INK)
    c.circle(x + 30, y + 84, 4, WHITE)
    c.circle(x + 88, y + 84, 10, INK)
    c.circle(x + 88, y + 84, 4, WHITE)
    for lx in (x + 8, x + 14, x + 20):
        c.hline(lx, y + 22, 10, col)


def draw_shop(c, x, y, col):
    # storefront with striped awning
    for i in range(5):
        stripe = col if i % 2 == 0 else GOLD
        c.polygon([(x + 8 + i * 21, y + 26), (x + 29 + i * 21, y + 26),
                   (x + 25 + i * 21, y + 46), (x + 12 + i * 21, y + 46)], stripe)
    c.fill_rect(x + 14, y + 46, 92, 52, col)
    c.fill_rect(x + 22, y + 56, 24, 42, WHITE)
    c.fill_rect(x + 74, y + 56, 24, 42, WHITE)
    c.fill_rect(x + 52, y + 62, 16, 36, GOLD)
    c.fill_rect(x + 14, y + 20, 92, 6, col)


def draw_ball(c, x, y, col):
    c.ellipse(x + 60, y + 60, 46, 30, col)
    c.line(x + 22, y + 44, x + 98, y + 76, WHITE)
    c.line(x + 22, y + 76, x + 98, y + 44, WHITE)
    c.circle(x + 60, y + 60, 7, WHITE)
    c.circle(x + 60, y + 60, 3, col)


# --- stories: verified 21 November 2026 reporting --------------------------
# Sources: Reuters (France marches, El Chapo Isidro, Wildberries, Ireland,
# Colturi), ISW (Sparta II drones, Zelensky ceasefire proposal), CNN and
# Reuters (Gaza strike, Kryvyi Rih). Every headline below states only what
# those reports said on 21 November 2026.
STORIES = [
    {
        "kicker": "UKRAINE",
        "accent": (29, 78, 137),
        "tint": (220, 232, 245),
        "headline": "UKRAINIAN DRONES HIT RUSSIAN SHIP SPARTA II",
        "summary": "DRONES HIT THE SPARTA II IN THE GULF OF FINLAND; ZELENSKY OFFERS LOCAL CEASEFIRES.",
        "pic": draw_ship,
    },
    {
        "kicker": "FRANCE",
        "accent": (176, 42, 48),
        "tint": (246, 222, 221),
        "headline": "COST-OF-LIVING MARCHES SHRINK ACROSS FRANCE",
        "summary": "82,500 MARCH NATIONWIDE, THE MINISTRY SAYS, DOWN ON LAST WEEK.",
        "pic": draw_crowd,
    },
    {
        "kicker": "MEXICO",
        "accent": (30, 122, 70),
        "tint": (221, 240, 228),
        "headline": "EL CHAPO ISIDRO CAPTURED IN MEXICO",
        "summary": "FAUSTO ISIDRO MEZA FLORES SEIZED IN SINALOA ON FRIDAY NIGHT.",
        "pic": draw_badge,
    },
    {
        "kicker": "GAZA",
        "accent": (185, 122, 15),
        "tint": (247, 235, 203),
        "headline": "THREE KILLED AS STRIKE HITS VEHICLE IN GAZA",
        "summary": "THREE DEAD IN GAZA CITY, HEALTH OFFICIALS SAY. AID LINK DISPUTED.",
        "pic": draw_truck,
    },
    {
        "kicker": "RUSSIA",
        "accent": (91, 58, 142),
        "tint": (230, 222, 242),
        "headline": "WILDBERRIES CHIEF QUITS AFTER EU SANCTIONS",
        "summary": "TATYANA KIM STEPS DOWN DAYS AFTER THE EU PUT HER ON ITS SANCTIONS LIST.",
        "pic": draw_shop,
    },
    {
        "kicker": "SPORT",
        "accent": (14, 110, 110),
        "tint": (216, 239, 234),
        "headline": "IRELAND BEAT SOUTH AFRICA 20-17, REACH FINAL",
        "summary": "SPRINGBOKS STILL REACH THE FINAL. COLTURI WINS ALBANIA'S FIRST SKI WORLD CUP.",
        "pic": draw_ball,
    },
]


def draw_panel(c, x, y, w, h, story):
    accent, tint = story["accent"], story["tint"]
    c.fill_rect(x, y, w, h, WHITE)
    c.fill_rect(x, y, w, 3, accent)
    c.fill_rect(x, y + h - 3, w, 3, accent)
    c.fill_rect(x, y, 3, h, accent)
    c.fill_rect(x + w - 3, y, 3, h, accent)
    # kicker bar
    c.fill_rect(x + 3, y + 3, w - 6, 30, accent)
    c.text(x + 16, y + 11, story["kicker"], 2, WHITE)
    # headline, up to two lines
    lines = wrap_text(story["headline"], 3, w - 32)
    hy = y + 44
    for line in lines[:2]:
        c.text(x + 16, hy, line, 3, INK)
        hy += 24
    # pictogram on a tinted tile, summary beside it
    pic_y = y + 116
    c.fill_rect(x + 16, pic_y, 120, 120, tint)
    story["pic"](c, x + 16, pic_y, accent)
    sx = x + 150
    slines = wrap_text(story["summary"], 3, w - 166)
    sy = pic_y + 6
    for line in slines[:5]:
        c.text(sx, sy, line, 3, BODY)
        sy += 22


def build_image():
    c = Canvas(W, H, PAPER)
    # masthead
    c.fill_rect(16, 16, 992, 118, NAVY)
    c.fill_rect(16, 130, 992, 4, GOLD)
    c.text_center(512, 30, "THE WORLD IN ONE DAY", 6, CREAM)
    c.text_center(512, 88, "SATURDAY 21 NOVEMBER 2026", 4, GOLD)
    # subhead
    c.text_center(512, 150, "SIX STORIES THAT DEFINED THE DAY", 3, INK)
    c.hline(16, 178, 380, RULE)
    c.hline(628, 178, 380, RULE)
    # story grid: 2 columns x 3 rows
    px, py = 16, 188
    pw, ph = 488, 252
    for i, story in enumerate(STORIES):
        x = px + (i % 2) * (pw + 16)
        y = py + (i // 2) * (ph + 12)
        draw_panel(c, x, y, pw, ph, story)
    # footer
    c.text_center(512, 968, "SOURCES: REUTERS, ISW, CNN - DRAWN BY CODE", 2, MUTED)
    return c.px


def encode_png(w, h, rgb):
    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(W, H, build_image())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, sha256 %s)" % (path, len(data), hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
