"""Output: SVG (glow filter) and PNG (own numpy/Pillow compositor; CairoSVG would drop the blur filters).

Look: one hue per circle. Lines are drawn in a near-white core tinted by the hue; the glow is the sum of three
Gaussian blurs of the line mask (tight / medium / wide) in the hue; the PNG tone-maps the sum (1 - exp(-x)) so
dense crossings burn toward white instead of clipping. Model space is y-up; SVG flips y.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np

GLOW = ((0.0045, 0.9), (0.014, 0.55), (0.045, 0.35))   # (sigma in model units, weight)


def hex_rgb(c: str):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(t):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in t)


def core_color(color: str, k: float = 0.62) -> str:
    r, g, b = hex_rgb(color)
    return rgb_hex((r + (255 - r) * k, g + (255 - g) * k, b + (255 - b) * k))


def extent(strokes, margin=0.06) -> float:
    m = 1.0
    for s in strokes:
        if len(s.pts):
            m = max(m, float(np.sqrt((s.pts ** 2).sum(1)).max()) + s.w)
    return max(1.1, m * (1 + margin) + 0.05)


# ---------------------------------------------------------------- SVG

def _f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _path_d(s) -> str:
    P = s.pts
    if s.circ is not None and len(P) >= 2:
        cx, cy, r = s.circ
        rad = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
        if np.allclose(rad, r, rtol=1e-4, atol=1e-5):
            a = np.unwrap(np.arctan2(P[:, 0] - cx, P[:, 1] - cy))
            span = float(a[-1] - a[0]) if not s.closed else 2 * math.pi
            if s.closed:
                return (f"M{_f(cx - r)},{_f(-cy)}a{_f(r)},{_f(r)} 0 1 0 {_f(2 * r)},0"
                        f"a{_f(r)},{_f(r)} 0 1 0 {_f(-2 * r)},0Z")
            x0, y0 = P[0]
            x1, y1 = P[-1]
            large = 1 if abs(span) > math.pi else 0
            sweep = 1 if span > 0 else 0          # clockwise in y-up == clockwise on screen after the flip
            if abs(span) > 1.9 * math.pi:          # nearly full: split to keep the arc well defined
                xm, ym = P[len(P) // 2]
                return (f"M{_f(x0)},{_f(-y0)}A{_f(r)},{_f(r)} 0 0 {sweep} {_f(xm)},{_f(-ym)}"
                        f"A{_f(r)},{_f(r)} 0 0 {sweep} {_f(x1)},{_f(-y1)}")
            return f"M{_f(x0)},{_f(-y0)}A{_f(r)},{_f(r)} 0 {large} {sweep} {_f(x1)},{_f(-y1)}"
    d = "M" + "L".join(f"{_f(x)},{_f(-y)}" for x, y in P)
    return d + ("Z" if s.closed else "")


def to_svg(strokes, color="#6fd8ff", size=512, background=None, glow=1.0, title="Magic circle", E=None,
           uid_seed="c") -> str:
    E = E or extent(strokes)
    uid = "m" + hashlib.blake2b(str(uid_seed).encode("utf-8"), digest_size=4).hexdigest()
    core = core_color(color)
    groups: dict[float, list[str]] = {}
    fills, erases = [], []
    for s in strokes:
        if s.erase:
            erases.append((s, _path_d(s)))
        elif s.fill:
            fills.append(_path_d(s))
        else:
            groups.setdefault(round(s.w, 5), []).append(_path_d(s))
    body = []
    for w, ds in sorted(groups.items(), reverse=True):
        body.append(f'<path d="{" ".join(ds)}" stroke-width="{_f(w)}"/>')
    if fills:
        body.append(f'<path d="{" ".join(fills)}" fill="{core}" stroke="none"/>')
    mask_attr, defs_mask = "", ""
    if erases:
        er = []
        for s, d in erases:
            if s.fill:
                er.append(f'<path d="{d}" fill="#000" stroke="none"/>')
            else:
                er.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{_f(s.w)}"/>')
        defs_mask = (f'<mask id="{uid}k" maskUnits="userSpaceOnUse" x="{_f(-E)}" y="{_f(-E)}" width="{_f(2 * E)}" '
                     f'height="{_f(2 * E)}"><rect x="{_f(-E)}" y="{_f(-E)}" width="{_f(2 * E)}" height="{_f(2 * E)}" '
                     f'fill="#fff"/>{"".join(er)}</mask>')
        mask_attr = f' mask="url(#{uid}k)"'
    (s1, a1), (s2, a2), (s3, a3) = [(sg * glow, a) for sg, a in GLOW]
    flt = (f'<filter id="{uid}g" x="{_f(-E)}" y="{_f(-E)}" width="{_f(2 * E)}" height="{_f(2 * E)}" '
           f'filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">'
           f'<feGaussianBlur in="SourceAlpha" stdDeviation="{_f(s1)}" result="b1"/>'
           f'<feGaussianBlur in="SourceAlpha" stdDeviation="{_f(s2)}" result="b2"/>'
           f'<feGaussianBlur in="SourceAlpha" stdDeviation="{_f(s3)}" result="b3"/>'
           f'<feComposite in="b1" in2="b2" operator="arithmetic" k2="{a1 * 1.4:.3f}" k3="{a2 * 1.6:.3f}" result="b12"/>'
           f'<feComposite in="b12" in2="b3" operator="arithmetic" k2="1" k3="{a3 * 1.8:.3f}" result="bs"/>'
           f'<feFlood flood-color="{color}"/><feComposite in2="bs" operator="in" result="gl"/>'
           f'<feMerge><feMergeNode in="gl"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    bg = (f'<rect x="{_f(-E)}" y="{_f(-E)}" width="{_f(2 * E)}" height="{_f(2 * E)}" fill="{background}"/>'
          if background else "")
    import html
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{_f(-E)} {_f(-E)} {_f(2 * E)} {_f(2 * E)}" '
            f'width="{size}" height="{size}"><title>{html.escape(title)}</title><defs>{flt}{defs_mask}</defs>{bg}'
            f'<g filter="url(#{uid}g)"><g{mask_attr} fill="none" stroke="{core}" stroke-linecap="round" '
            f'stroke-linejoin="round">{"".join(body)}</g></g></svg>')


# ---------------------------------------------------------------- PNG

def masks(strokes, E, px, ss=3):
    """Core mask and glow-source mask (per-stroke glow weight), supersampled then reduced."""
    from PIL import Image, ImageDraw
    S = px * ss
    k = S / (2 * E)
    core = Image.new("L", (S, S), 0)
    gsrc = Image.new("L", (S, S), 0)
    dc, dg = ImageDraw.Draw(core), ImageDraw.Draw(gsrc)

    def tr(P):
        return [((x + E) * k, (E - y) * k) for x, y in P]

    order = [s for s in strokes if not s.erase] + [s for s in strokes if s.erase]
    for s in order:
        val_c = 0 if s.erase else 255
        val_g = 0 if s.erase else int(255 * min(1.0, s.glow))
        pts = tr(s.pts)
        if s.fill:
            if len(pts) >= 3:
                dc.polygon(pts, fill=val_c)
                dg.polygon(pts, fill=val_g)
            continue
        wpx = max(1.0, s.w * k)
        if s.closed:
            pts = pts + pts[:1]
        iw = int(round(wpx))
        dc.line(pts, fill=val_c, width=iw, joint="curve")
        dg.line(pts, fill=val_g, width=iw, joint="curve")
        if not s.closed and wpx > 2:
            rr = wpx / 2
            for (x, y) in (pts[0], pts[-1]):
                dc.ellipse((x - rr, y - rr, x + rr, y + rr), fill=val_c)
                dg.ellipse((x - rr, y - rr, x + rr, y + rr), fill=val_g)
    core = core.resize((px, px), Image.BOX)
    gsrc = gsrc.resize((px, px), Image.BOX)
    return core, gsrc


def to_png(strokes, path=None, color="#6fd8ff", size=512, background=(12, 12, 20), glow=1.0, E=None):
    """background: RGB tuple, or None for a transparent PNG."""
    from PIL import Image, ImageFilter
    E = E or extent(strokes)
    core, gsrc = masks(strokes, E, size)
    px_per = size / (2 * E)
    G = np.zeros((size, size), np.float32)
    for sg, a in GLOW:
        rad = max(0.6, sg * glow * px_per)
        G += a * np.asarray(gsrc.filter(ImageFilter.GaussianBlur(rad)), np.float32) / 255.0
    C = np.asarray(core, np.float32) / 255.0
    hue = np.array(hex_rgb(color), np.float32) / 255.0
    cc = np.array(hex_rgb(core_color(color)), np.float32) / 255.0
    light = G[..., None] * hue * 2.2 + C[..., None] * cc * 1.6
    L = 1.0 - np.exp(-light)                       # tone map: bright overlaps go white-ish, never clip hard
    if background is None:
        a = L.max(axis=2, keepdims=True)
        rgb = np.where(a > 1e-6, L / np.maximum(a, 1e-6), 0)
        arr = np.concatenate([rgb, a], axis=2)
        im = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    else:
        bg = np.array(background, np.float32) / 255.0
        out = 1 - (1 - bg) * (1 - L)               # screen: emitted light over the background
        im = Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
    if path:
        im.save(path)
    return im
