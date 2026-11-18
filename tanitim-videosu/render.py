"""Tanıtım videosu üretici.

Kullanım:
  python3 render.py 169            # 16:9 ana video
  python3 render.py 916            # 9:16 kısa kesit
  python3 render.py 169 --still 12 # 12. saniyeden tek kare (kontrol için)
"""
import argparse
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

import timeline as T

HERE = os.path.dirname(os.path.abspath(__file__))
FOTO_DIR = os.path.join(HERE, "fotograflar")
OUT_DIR = os.path.join(HERE, "cikti")
FPS = 30
TR = 0.8  # geçiş süresi

FD = "/usr/share/fonts/opentype/inter/"
F_BLACK = FD + "InterDisplay-Black.otf"
F_BOLD = FD + "InterDisplay-Bold.otf"
F_SEMI = FD + "Inter-SemiBold.otf"

RED = (200, 68, 43)
ORANGE = (240, 138, 36)
CREAM = (255, 244, 226)
BROWN = (59, 36, 22)


def font(path, size):
    return ImageFont.truetype(path, size)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def wrap(text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if fnt.getlength(test) <= maxw or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def shadowed(img, radius=18, offset=(0, 10), alpha=150):
    """RGBA görsele yumuşak gölge ekler (kenar boşluğuyla)."""
    pad = radius * 3
    W, H = img.size
    out = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: v * alpha // 255)
    blk = Image.new("RGBA", img.size, (20, 10, 5, 255))
    blk.putalpha(a)
    sh.paste(blk, (pad + offset[0], pad + offset[1]))
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    out = Image.alpha_composite(out, sh)
    out.alpha_composite(img, (pad, pad))
    return out, pad


# =================================================================== Fotoğraflar
def warm_grade(im):
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    a = a * np.array([1.04, 1.0, 0.93]) + np.array([0.012, 0.004, -0.004])
    a = np.clip(a, 0, 1) ** 0.96
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def placeholder(slot, tarif, size):
    W, H = size
    g = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    r = 70 + 60 * x + 20 * g
    gg = 38 + 30 * x + 10 * g
    b = 24 + 10 * x
    stripes = ((np.add.outer(np.arange(H), np.arange(W)) // 40) % 2) * 6
    arr = np.stack([r + stripes, gg + stripes, b + stripes], -1)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    s = min(W, H)
    f1, f2, f3 = font(F_BLACK, s // 7), font(F_SEMI, s // 22), font(F_SEMI, s // 30)
    cx, cy = W // 2, H // 2
    d.rounded_rectangle([cx - s * 0.42, cy - s * 0.25, cx + s * 0.42, cy + s * 0.25],
                        radius=30, outline=CREAM + (0,), width=4)
    d.text((cx, cy - s * 0.08), slot, font=f1, fill=CREAM, anchor="mm")
    for k, ln in enumerate(wrap(tarif, f2, s * 0.75)):
        d.text((cx, cy + s * 0.06 + k * s * 0.05), ln, font=f2, fill=(255, 210, 160), anchor="mm")
    d.text((cx, cy + s * 0.2), "OKUL FOTOĞRAFI BEKLENİYOR", font=f3, fill=(255, 190, 120), anchor="mm")
    return im


def load_slot(slot, photos, size):
    info = photos.get(slot) or {}
    fn = info.get("dosya")
    if fn:
        p = os.path.join(FOTO_DIR, fn)
        im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        return warm_grade(im), True
    return placeholder(slot, info.get("tarif", ""), size), False


def cover(im, W, H):
    s = max(W / im.width, H / im.height)
    im = im.resize((max(W, round(im.width * s)), max(H, round(im.height * s))), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((l, t, l + W, t + H))


def contain(im, W, H):
    s = min(W / im.width, H / im.height)
    return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)


class Shot:
    OVERS = 1.22

    def __init__(self, slot, move, start, end, photos, W, H, idx):
        self.slot, self.move, self.start, self.end, self.W, self.H = slot, move, start, end, W, H
        self.idx = idx
        src, real = load_slot(slot, photos, (W, H))
        ow, oh = int(W * self.OVERS), int(H * self.OVERS)
        self.big = cover(src, ow, oh)
        if move == "parallax":
            bg = cover(src, ow, oh).filter(ImageFilter.GaussianBlur(28))
            bg = Image.blend(bg, Image.new("RGB", bg.size, BROWN), 0.45)
            self.bg = bg
            fw, fh = (int(W * 0.66), int(H * 0.74)) if W > H else (int(W * 0.86), int(H * 0.50))
            fg = contain(src, fw, fh).convert("RGBA")
            m = Image.new("L", fg.size, 0)
            ImageDraw.Draw(m).rounded_rectangle([0, 0, fg.width - 1, fg.height - 1], radius=26, fill=255)
            fg.putalpha(m)
            border = Image.new("RGBA", (fg.width + 16, fg.height + 16), (0, 0, 0, 0))
            ImageDraw.Draw(border).rounded_rectangle([0, 0, border.width - 1, border.height - 1],
                                                     radius=32, fill=CREAM + (255,))
            border.alpha_composite(fg, (8, 8))
            self.fg, self.fg_pad = shadowed(border, 22, (0, 16), 170)

    def crop_view(self, img, z, cx, cy):
        """img (OVERS ölçekli) içinden z yakınlaşmasıyla W×H kare."""
        W, H = self.W, self.H
        bw, bh = W * self.OVERS / z, H * self.OVERS / z
        bw, bh = min(bw, img.width), min(bh, img.height)
        x0 = (img.width - bw) * cx
        y0 = (img.height - bh) * cy
        return img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh))

    def frame(self, t):
        p = (t - (self.start - TR / 2)) / ((self.end - self.start) + TR)
        p = min(max(p, 0), 1)
        m = self.move
        if m == "zoom_in":
            return self.crop_view(self.big, 1.0 + 0.16 * ease_io(p), 0.5 + 0.04 * p, 0.45)
        if m == "zoom_out":
            return self.crop_view(self.big, 1.18 - 0.16 * ease_io(p), 0.5, 0.5 - 0.04 * p)
        if m == "pan_r":
            return self.crop_view(self.big, 1.05, 0.08 + 0.84 * ease_io(p), 0.5)
        if m == "pan_l":
            return self.crop_view(self.big, 1.05, 0.92 - 0.84 * ease_io(p), 0.5)
        # parallax: arka plan yavaş sola, ön plan hızlı sağa
        bg = self.crop_view(self.bg, 1.02 + 0.08 * p, 0.7 - 0.4 * p, 0.5).convert("RGBA")
        W, H = self.W, self.H
        fw, fh = self.fg.size
        dx = (-0.035 + 0.07 * ease_io(p)) * W
        dy = (-0.01 + 0.02 * p) * H
        if W > H:
            x = int(W * 0.60 - fw / 2 + dx)
        else:
            x = int(W / 2 - fw / 2 + dx)
        y = int(H / 2 - fh / 2 + dy - (0 if W > H else H * 0.06))
        _paste(bg, self.fg, x, y)
        return bg.convert("RGB")


def _paste(dst, src, x, y):
    dst.paste(src, (x, y), src)


# =================================================================== Kartlar
def pill(text, fnt, fill, color, padx=34, pady=18, radius=None):
    w = int(fnt.getlength(text)) + 2 * padx
    asc, desc = fnt.getmetrics()
    h = asc + desc + 2 * pady
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius or h // 2, fill=fill)
    d.text((padx, pady), text, font=fnt, fill=color)
    return im


def panel(lines, fnts, colors, maxw, pad=44, gap=14, accent=True, fill=CREAM + (245,)):
    rows = []
    for txt, f, c in zip(lines, fnts, colors):
        for ln in wrap(txt, f, maxw):
            rows.append((ln, f, c))
    w = max(int(f.getlength(l)) for l, f, _ in rows) + 2 * pad + (14 if accent else 0)
    hs = [sum(f.getmetrics()) for _, f, _ in rows]
    h = sum(hs) + gap * (len(rows) - 1) + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=28, fill=fill)
    if accent:
        d.rounded_rectangle([0, 0, 14, h - 1], radius=7, fill=ORANGE + (255,))
    y = pad
    for (ln, f, c), hh in zip(rows, hs):
        d.text((pad + (14 if accent else 0), y), ln, font=f, fill=c)
        y += hh + gap
    return shadowed(im, 20, (0, 12), 140)


class Card:
    """Ekrana giren grafik öğe: (görsel, hedef konum, giriş yönü, zaman aralığı)."""

    def __init__(self, img, pad, x, y, t0, t1, frm="left"):
        self.img, self.pad, self.x, self.y, self.t0, self.t1, self.frm = img, pad, x, y, t0, t1, frm

    def draw(self, canvas, t, W, H):
        if t < self.t0 or t > self.t1:
            return
        a_in = ease_out((t - self.t0) / 0.55)
        a_out = ease_io((self.t1 - t) / 0.4)
        a = min(a_in, a_out)
        if a <= 0.01:
            return
        dist = 120 * (1 - a_in)
        dx, dy = {"left": (-dist, 0), "right": (dist, 0), "up": (0, dist), "down": (0, -dist)}[self.frm]
        im = self.img
        if a < 0.999:
            im = im.copy()
            im.putalpha(im.split()[3].point(lambda v: int(v * a)))
        _paste(canvas, im, int(self.x - self.pad + dx), int(self.y - self.pad + dy))


def build_cards(tl, W, H):
    wide = W > H
    S = W / 1920 if wide else W / 1080
    cards, dings = [], []
    f_q = font(F_BLACK, int((92 if wide else 96) * S))
    f_t = font(F_BLACK, int((84 if wide else 80) * S))
    f_s = font(F_SEMI, int((44 if wide else 46) * S))
    f_l = font(F_BOLD, int((54 if wide else 58) * S))
    f_tag = font(F_BLACK, int((40 if wide else 44) * S))
    for sc in tl["scenes"]:
        shots = sc["_shots"]
        for c in sc["cards"]:
            k = c["kind"]
            if "shot" in c:
                sh = shots[c["shot"]]
                t0, t1 = sh.start + 0.35, sh.end - 0.2
            else:
                t0, t1 = sc["start"] + c["at"], sc["end"] - 0.25
            if k in ("question", "cta"):
                maxw = W * (0.8 if wide else 0.84)
                im, pad = panel([c["title"]], [f_q], [BROWN], maxw, pad=54)
                x = (W - (im.width - 2 * pad)) / 2
                y = H * (0.30 if wide else 0.22)
                cards.append(Card(im, pad, x, y, t0, t1, "up"))
            elif k == "title":
                im, pad = panel([c["title"], c["sub"]], [f_t, f_s], [RED, BROWN], W * 0.8)
                x, y = (W * 0.06, H * 0.42) if wide else (W * 0.07, H * 0.12)
                cards.append(Card(im, pad, x, y, t0, t1, "left"))
            elif k == "info":
                tag = pill(c["title"], f_tag, ORANGE + (255,), (255, 255, 255))
                tg, tp = shadowed(tag, 14, (0, 8), 120)
                im, pad = panel([c["sub"]], [f_l], [BROWN], W * (0.30 if wide else 0.78))
                if wide:
                    x, y = W * 0.05, H * 0.36
                else:
                    x, y = W * 0.08, H * 0.11
                cards.append(Card(tg, tp, x, y, t0, t1, "left"))
                cards.append(Card(im, pad, x, y + tag.height + 18 * S, t0 + 0.15, t1, "left"))
            elif k == "label":
                tag = pill(c["title"], f_tag, RED + (255,), CREAM)
                tg, tp = shadowed(tag, 14, (0, 8), 120)
                x, y = (W * 0.05, H * 0.07) if wide else (W * 0.08, H * 0.08)
                cards.append(Card(tg, tp, x, y, t0, t1, "down"))
            elif k == "list":
                tag = pill(c["title"], f_tag, RED + (255,), CREAM)
                tg, tp = shadowed(tag, 14, (0, 8), 120)
                if wide:
                    x0, y0 = W * 0.06, H * 0.16
                else:
                    x0, y0 = W * 0.08, H * 0.09
                cards.append(Card(tg, tp, x0, y0, t0, t1, "down"))
                yy = y0 + tag.height + 26 * S
                for j, it in enumerate(c["items"]):
                    pl = pill("•  " + it, f_l, CREAM + (240,), BROWN, padx=30, pady=14, radius=22)
                    pg, pp = shadowed(pl, 14, (0, 8), 120)
                    cards.append(Card(pg, pp, x0, yy, t0 + 0.5 + j * 0.55, t1, "left"))
                    dings.append(t0 + 0.5 + j * 0.55)
                    yy += pl.height + 16 * S
                continue
            elif k == "names":
                tag = pill(c["title"], f_tag, RED + (255,), CREAM)
                tg, tp = shadowed(tag, 14, (0, 8), 120)
                x0 = W * 0.06 if wide else W * 0.08
                y0 = H * 0.12 if wide else H * 0.12
                cards.append(Card(tg, tp, x0, y0, t0, t1, "down"))
                yy = y0 + tag.height + 26 * S
                for j, nm in enumerate(c["items"]):
                    im, pad = panel([nm, "Alan Öğretmeni"], [f_t, f_s], [RED, BROWN], W * 0.8)
                    cards.append(Card(im, pad, x0, yy, t0 + 0.4 + j * 0.6, t1, "left"))
                    dings.append(t0 + 0.4 + j * 0.6)
                    yy += im.height - 2 * pad + 24 * S
                continue
            dings.append(t0)
    return cards, dings


def build_endcard(W, H):
    wide = W > H
    S = W / 1920 if wide else W / 1080
    y = np.linspace(0, 1, H)[:, None, None]
    x = np.linspace(0, 1, W)[None, :, None]
    base = np.array(BROWN, np.float32) * (1 - 0.35 * y) + np.array(RED, np.float32) * 0.35 * (x * (1 - y))
    bg = Image.fromarray(np.clip(base + 0 * x, 0, 255).astype(np.uint8)).convert("RGBA")
    f1 = font(F_BLACK, int((64 if wide else 72) * S))
    f2 = font(F_BOLD, int((48 if wide else 52) * S))
    f3 = font(F_SEMI, int((40 if wide else 44) * S))
    maxw = W * (0.82 if wide else 0.86)
    items = []  # (img, y, delay)
    yy = H * (0.18 if wide else 0.24)
    for ln in wrap(T.ENDCARD["title"], f1, maxw):
        items.append((ln, f1, CREAM, yy))
        yy += sum(f1.getmetrics()) + 6 * S
    yy += 20 * S
    items.append((T.ENDCARD["sub"], f2, ORANGE, yy))
    yy += sum(f2.getmetrics()) + 50 * S
    for r in T.ENDCARD["rows"]:
        for ln in wrap(r, f3, maxw):
            items.append((ln, f3, (255, 225, 190), yy))
            yy += sum(f3.getmetrics()) + 14 * S
    yy += 40 * S
    items.append(("Seni de mutfağımıza bekliyoruz!", f2, CREAM, yy))
    rendered = []
    for k, (txt, f, col, yv) in enumerate(items):
        w = int(f.getlength(txt)) + 10
        hh = sum(f.getmetrics()) + 10
        im = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((5, 5), txt, font=f, fill=col)
        rendered.append((im, (W - w) / 2, yv, k * 0.18))
    return bg, rendered


# =================================================================== Altyazı
def build_subs(tl, W, H):
    wide = W > H
    S = W / 1920 if wide else W / 1080
    f = font(F_BOLD, int((60 if wide else 66) * S))
    out = []
    for s in tl["subs"]:
        lines = wrap(s["text"], f, W * (0.82 if wide else 0.84))
        lh = sum(f.getmetrics()) + 6
        w = max(int(f.getlength(l)) for l in lines) + 70
        h = lh * len(lines) + 40
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=24, fill=(25, 14, 8, 190))
        for k, ln in enumerate(lines):
            col = (255, 214, 120) if "[BOŞLUK" in ln else (255, 255, 255)
            d.text((w / 2, 20 + k * lh), ln, font=f, fill=col, anchor="ma",
                   stroke_width=2, stroke_fill=(0, 0, 0))
        x = (W - w) / 2
        y = (H * 0.955 - h) if wide else (H * 0.74 - h / 2)
        out.append((im, x, y, s["start"], s["end"]))
    return out


# =================================================================== Sahne kurulumu
class Film:
    def __init__(self, fmt):
        self.fmt = fmt
        self.W, self.H = (1920, 1080) if fmt == "169" else (1080, 1920)
        scenes = T.SCENES_169 if fmt == "169" else T.SCENES_916
        self.tl = T.build(scenes)
        photos = T.load_photos()
        self.shots, self.transitions = [], []
        idx = 0
        for sc in self.tl["scenes"]:
            sc["_shots"] = []
            n = len(sc["shots"])
            if sc.get("endcard"):
                self.endcard = (sc["start"], sc["end"])
                self.transitions.append(sc["start"])
                continue
            d = (sc["end"] - sc["start"]) / n
            for k, (slot, mv) in enumerate(sc["shots"]):
                sh = Shot(slot, mv, sc["start"] + k * d, sc["start"] + (k + 1) * d, photos,
                          self.W, self.H, idx)
                idx += 1
                self.shots.append(sh)
                sc["_shots"].append(sh)
                if sh.start > 0.01:
                    self.transitions.append(sh.start)
        self.total = self.tl["total"]
        self.cards, self.dings = build_cards(self.tl, self.W, self.H)
        self.subs = build_subs(self.tl, self.W, self.H)
        self.end_bg, self.end_items = build_endcard(self.W, self.H)
        self._fx()

    def _fx(self):
        W, H = self.W, self.H
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        self.vig = (1 - 0.38 * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)
        # ışık sızıntısı dokusu (2× genişlik, kaydırılarak kullanılır)
        LW, LH = W * 2, H
        ly, lx = np.mgrid[0:LH:4, 0:LW:4].astype(np.float32)
        leak = np.zeros(ly.shape + (3,), np.float32)
        rng = np.random.default_rng(3)
        for _ in range(6):
            cx, cy = rng.uniform(0, LW), rng.uniform(-0.2, 1.2) * LH
            rad = rng.uniform(0.25, 0.5) * LH
            col = np.array(rng.choice([ORANGE, RED, (255, 190, 90)]), np.float32) / 255
            g = np.exp(-(((lx - cx) ** 2 + (ly - cy) ** 2) / (2 * rad ** 2)))
            leak += g[..., None] * col
        leak = np.clip(leak, 0, 1)
        self.leak = np.asarray(Image.fromarray((leak * 255).astype(np.uint8)).resize((LW, LH), Image.BILINEAR),
                               np.float32) / 255

    def shot_frame(self, sh, t):
        return np.asarray(sh.frame(t), np.float32) / 255

    def frame(self, t):
        W, H = self.W, self.H
        # --- taban görüntü
        if hasattr(self, "endcard") and t >= self.endcard[0] - TR / 2:
            canvas = self.end_bg.copy()
            for im, x, y, dl in self.end_items:
                a = ease_out((t - self.endcard[0] - 0.3 - dl) / 0.6)
                if a > 0:
                    m = im.copy()
                    m.putalpha(m.split()[3].point(lambda v: int(v * a)))
                    _paste(canvas, m, int(x), int(y + 40 * (1 - a)))
            base = np.asarray(canvas.convert("RGB"), np.float32) / 255
            if t < self.endcard[0] + TR / 2 and self.shots:
                w = ease_io((t - (self.endcard[0] - TR / 2)) / TR)
                base = base * w + self.shot_frame(self.shots[-1], t) * (1 - w)
        else:
            cur = [s for s in self.shots if s.start - TR / 2 <= t < s.end + TR / 2]
            if len(cur) >= 2:
                a, b = cur[0], cur[1]
                w = ease_io((t - (b.start - TR / 2)) / TR)
                base = self.shot_frame(a, t) * (1 - w) + self.shot_frame(b, t) * w
            elif cur:
                base = self.shot_frame(cur[0], t)
            else:
                base = np.zeros((H, W, 3), np.float32)
        # --- renk/vinyet
        base = base * self.vig
        # --- ışık sızıntısı (sürekli hafif + geçişlerde parlama)
        flash = 0.0
        for tt in self.transitions:
            flash = max(flash, math.exp(-((t - tt) / 0.28) ** 2))
        if t < 0.6:
            flash = max(flash, 1 - t / 0.6)
        off = int((t * 0.04 % 1) * W)
        lk = self.leak[:, off:off + W]
        k = 0.10 + 0.55 * flash
        base = 1 - (1 - base) * (1 - lk * k)
        if t < 0.25:  # siyahtan açılış
            base = base * (t / 0.25)
        img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        # --- kartlar ve altyazı
        for c in self.cards:
            c.draw(img, t, W, H)
        for im, x, y, t0, t1 in self.subs:
            if t0 - 0.12 <= t <= t1 + 0.12:
                a = min(ease_out((t - t0 + 0.12) / 0.2), ease_out((t1 + 0.12 - t) / 0.2))
                m = im
                if a < 0.999:
                    m = im.copy()
                    m.putalpha(m.split()[3].point(lambda v: int(v * a)))
                _paste(img, m, int(x), int(y))
        # son kararma
        if t > self.total - 0.8:
            img = Image.blend(img, Image.new("RGBA", img.size, (0, 0, 0, 255)),
                              ease_io((t - (self.total - 0.8)) / 0.8))
        return img.convert("RGB")


# =================================================================== Çıktı
_FILM = None


def _init(fmt):
    global _FILM
    _FILM = Film(fmt)


def _render_chunk(args):
    fmt, i0, i1, path = args
    f = _FILM
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{f.W}x{f.H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(f.frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return path


def vo_list(tl):
    out = []
    for s in tl["subs"]:
        pth = T.vo_path(s["id"])
        if os.path.exists(pth):
            out.append((s["start"], pth))
    return out


def main():
    import ses
    ap = argparse.ArgumentParser()
    ap.add_argument("fmt", choices=["169", "916"])
    ap.add_argument("--still", type=float)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    a = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    if a.still is not None:
        f = Film(a.fmt)
        p = os.path.join(OUT_DIR, f"kare_{a.fmt}_{a.still:.1f}.png")
        f.frame(a.still).save(p)
        print(p)
        return
    film = Film(a.fmt)
    n = int(film.total * FPS)
    print(f"{a.fmt}: {film.total:.1f} sn, {n} kare")
    tmp = os.path.join(OUT_DIR, "_parcalar")
    os.makedirs(tmp, exist_ok=True)
    step = math.ceil(n / a.jobs)
    jobs = [(a.fmt, i, min(n, i + step), os.path.join(tmp, f"{a.fmt}_{k:02d}.mp4"))
            for k, i in enumerate(range(0, n, step))]
    with Pool(a.jobs, initializer=_init, initargs=(a.fmt,)) as pool:
        parts = pool.map(_render_chunk, jobs)
    lst = os.path.join(tmp, f"{a.fmt}.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in parts)
    wav = os.path.join(tmp, f"{a.fmt}.wav")
    vos = vo_list(film.tl)
    ses.build_mix(film.tl, film.transitions, film.dings, wav, vos)
    suffix = "" if vos else "_TASLAK_seslendirmesiz"
    name = {"169": "tanitim_16x9", "916": "reels_9x16"}[a.fmt] + suffix + ".mp4"
    out = os.path.join(OUT_DIR, name)
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                           "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                           "-shortest", "-movflags", "+faststart", out])
    # altyazı dosyası (SRT) da üret
    srt = out.replace(".mp4", ".srt")
    with open(srt, "w", encoding="utf-8") as fh:
        for k, s in enumerate(film.tl["subs"], 1):
            def ts(x):
                h, r = divmod(x, 3600)
                m, r = divmod(r, 60)
                return f"{int(h):02d}:{int(m):02d}:{int(r):02d},{int((r % 1) * 1000):03d}"
            fh.write(f"{k}\n{ts(s['start'])} --> {ts(s['end'])}\n{s['text']}\n\n")
    print(out)


if __name__ == "__main__":
    main()
