"""Ring lines and band contents (research/visual_refs.md §3.2: the band vocabulary of the references).

Rings: {"r", "style": line | double | dashed | dotted | broken | heavy2, "tier", ...}
Bands: {"kind", "ri", "ro", ...params} fill the annulus [ri, ro] of a disc (local units, disc radius 1).
Every count is locked to the disc's symmetry order n (m = n·j) by the sampler; `phase` (deg) aligns items with
the figure. Builders receive `ctx` with: rng (build-time details), scripts (alphabets), sep, n, avoid (list of
(angle, half-span) where nodes sit on the band), z levels and a unique tag prefix.
"""
from __future__ import annotations

import math

import numpy as np

from . import script, symbols
from .canvas import polar


def _free(avoid, a, margin=0.0):
    for c, h in avoid:
        d = abs((a - c + 180) % 360 - 180)
        if d < h + margin:
            return False
    return True


def free_arcs(avoid, breaks=(), brk_half=0.0):
    """Complement of the avoid spans (+ symmetric breaks) as [(a0, a1)] with 0 <= a0 < a1."""
    spans = list(avoid) + [(b, brk_half) for b in breaks]
    if not spans:
        return [(0.0, 360.0)]
    iv = []
    for c, h in spans:
        a0, a1 = (c - h) % 360, (c + h) % 360
        if a0 <= a1:
            iv.append((a0, a1))
        else:
            iv += [(a0, 360.0), (0.0, a1)]
    iv.sort()
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    free = []
    for (a0, a1), (b0, _) in zip(merged, merged[1:] + [(merged[0][0] + 360, 0)]):
        if b0 - a1 > 1e-6:
            free.append((a1, b0))
    return free


# ---------------------------------------------------------------- rings

def ring(cv, spec, z, n=1, phase=0.0, tags=()):
    r, st, tier = spec["r"], spec.get("style", "line"), spec.get("tier", "thin")
    if st == "line":
        cv.circle(r, tier=tier, z=z, tags=tags)
    elif st == "double":
        g = spec.get("gap", 0.018)
        cv.circle(r, tier=tier, z=z, tags=tags)
        cv.circle(r - g, tier="hair" if tier != "hair" else "hair", z=z, tags=tags)
    elif st == "heavy2":
        g = spec.get("gap", 0.02)
        cv.circle(r, tier="heavy", z=z, tags=tags)
        cv.circle(r - g, tier="hair", z=z, tags=tags)
    elif st == "dashed":
        m = spec.get("m", n * 12)
        duty = spec.get("duty", 0.55)
        for i in range(m):
            a = phase + i * 360 / m
            cv.arc(r, a, a + duty * 360 / m, tier=tier, z=z, tags=tags)
    elif st == "dotted":
        m = spec.get("m", n * 16)
        for i in range(m):
            x, y = polar(r, phase + i * 360 / m)
            cv.dot(spec.get("dr", 0.006), x, y, z=z, tags=tags)
    elif st == "triple":
        g = spec.get("gap", 0.018)
        cv.circle(r, tier="hair", z=z, tags=tags)
        cv.circle(r - g, tier=tier, z=z, tags=tags)
        cv.circle(r - 2 * g, tier="hair", z=z, tags=tags)
    elif st == "scallop":                          # ring with a lobed crest outside it
        cv.circle(r, tier=tier, z=z, tags=tags)
        m = spec.get("m", n * 8)
        h = spec.get("h", 0.035)
        for i in range(m):
            a = phase + i * 360.0 / m
            t = np.linspace(0, 1, 16)
            cv.poly([polar(r + h * math.sin(math.pi * u), a + u * 360.0 / m) for u in t], False, "hair", z, tags)
    elif st == "teeth":                            # ring with small outward teeth
        cv.circle(r, tier=tier, z=z, tags=tags)
        m = spec.get("m", n * 12)
        h = spec.get("h", 0.03)
        for i in range(m):
            a = phase + i * 360.0 / m
            w = 360.0 / m * 0.25
            cv.poly([polar(r, a - w), polar(r + h, a - w * 0.6), polar(r + h, a + w * 0.6), polar(r, a + w)], False,
                    "hair", z, tags)
    elif st == "broken":                           # n arcs with gaps at the symmetry positions
        gap = spec.get("gapdeg", 10)
        k = spec.get("m", n)
        for i in range(k):
            a = phase + i * 360 / k + gap / 2
            cv.arc(r, a, a + 360 / k - gap, tier=tier, z=z, tags=tags)


# ---------------------------------------------------------------- band contents

def _positions(m, phase, avoid, margin=0.0):
    return [phase + i * 360.0 / m for i in range(m) if _free(avoid, phase + i * 360.0 / m, margin)]


def b_text(cv, b, ctx):
    alpha = ctx["scripts"][b.get("script", 0) % len(ctx["scripts"])]
    sep = ctx["seps"][b.get("script", 0) % len(ctx["seps"])]
    rng = ctx["rng"]
    segs = b.get("segments", 1)
    breaks = [ctx["phase"] + b.get("brk_phase", 0) + i * 360 / segs for i in range(segs)] if segs > 1 else []
    brk_half = b.get("brk_half", 4.0) if segs > 1 else 0.0
    arcs = free_arcs(ctx["avoid"], breaks, brk_half)
    for a0, a1 in arcs:
        toks = script.text_tokens(rng, alpha, sep, 400)
        script.lay_arc(cv, alpha, toks, sep, b["ri"], b["ro"], a0, a1, b.get("fill", 0.62), b.get("inward", False),
                       b.get("tier", "hair"), ctx["zg"], ctx["tags"])
    # ornaments in the breaks
    orn = b.get("brk_orn", "none")
    if segs > 1 and orn != "none":
        rm = (b["ri"] + b["ro"]) / 2
        h = (b["ro"] - b["ri"]) * 0.32
        for a in breaks:
            if not _free(ctx["avoid"], a):
                continue
            x, y = polar(rm, a)
            if orn == "dot":
                cv.dot(h * 0.35, x, y, z=ctx["zg"], tags=ctx["tags"])
            elif orn == "ring":
                cv.circle(h * 0.6, x, y, tier="hair", z=ctx["zg"], tags=ctx["tags"])
            else:
                g = symbols.sparkle(4, 0.15) if orn == "sparkle" else symbols.symbol("star", rng) if orn == "star" \
                    else {"s": [[(0.5, 0.05), (0.95, 0.5), (0.5, 0.95), (0.05, 0.5), (0.5, 0.05)]], "c": [], "w": 1}
                script.draw_glyph(cv, g, x, y, h * 2.0, rot=a, tier="hair", z=ctx["zg"], tags=ctx["tags"])


def b_inverted(cv, b, ctx):
    """Solid band with the text knocked out."""
    rm = (b["ri"] + b["ro"]) / 2
    cv.circle(rm, tier=(b["ro"] - b["ri"]) * ctx["s"], z=ctx["zr"], tags=ctx["tags"])
    alpha = ctx["scripts"][b.get("script", 0) % len(ctx["scripts"])]
    sep = ctx["seps"][0]
    sub = _Eraser(cv, ctx["W"]["thin"] * 1.6)
    for a0, a1 in free_arcs(ctx["avoid"]):
        toks = script.text_tokens(ctx["rng"], alpha, sep, 400)
        script.lay_arc(sub, alpha, toks, sep, b["ri"], b["ro"], a0, a1, 0.66, b.get("inward", False), "thin",
                       ctx["zg"], ctx["tags"])


class _Eraser:
    """Canvas proxy: everything drawn through it knocks ink out."""

    def __init__(self, cv, w):
        self.cv, self.wd = cv, w

    def poly(self, pts, closed=False, tier="thin", z=0.0, tags=()):
        st = self.cv.poly(pts, closed, self.wd, z, tags)
        if st is not None:
            st.erase = True

    def circle(self, r, cx=0.0, cy=0.0, tier="thin", z=0.0, tags=()):
        st = self.cv.circle(r, cx, cy, self.wd, z, tags)
        if st is not None:
            st.erase = True

    def dot(self, r, cx=0.0, cy=0.0, z=0.0, tags=()):
        st = self.cv.dot(r, cx, cy, z, tags)
        if st is not None:
            st.erase = True


def _symbol_for(src, ctx, i):
    rng = ctx["rng"]
    if src == "script":
        alpha = ctx["scripts"][0]
        g = alpha[rng.randrange(len(alpha))]
        return g, True
    if src == "numeral":
        return script.roman(i + 1), True
    if src == "zodiac":
        from .library import node_set
        z = [g for g in node_set("hershey_astro")]
        return z[i % len(z)], False
    if src == "trigram":
        bits = [(i >> k) & 1 for k in range(3)]
        return symbols.trigram(bits), False
    if src == "geomantic":
        return symbols.geomantic([(i >> k) % 2 + 1 for k in range(4)]), False
    return symbols.symbol(src, rng, ctx["scripts"][0]), False


def b_glyphs(cv, b, ctx):
    m = b["m"]
    rm = (b["ri"] + b["ro"]) / 2
    h = (b["ro"] - b["ri"]) * b.get("size", 0.7)
    frame = b.get("frame", "none")
    fixed = b.get("fixed", False)                       # same symbol everywhere (rotational symmetry kept)
    first = None
    for i, a in enumerate(_positions(m, ctx["phase"] + b.get("phase", 0), ctx["avoid"], 360 / m / 3)):
        idx = int(round((a - ctx["phase"] - b.get("phase", 0)) / (360 / m))) % m
        if fixed and first is not None:
            g, text = first
        else:
            g, text = _symbol_for(b.get("src", "script"), ctx, idx)
            first = (g, text)
        x, y = polar(rm, a)
        rot = a if b.get("orient", "radial") == "radial" else 0.0
        if frame == "circle":
            cv.circle(h * 0.62, x, y, tier="hair", z=ctx["zg"], tags=ctx["tags"])
        elif frame == "square":
            q = h * 0.58
            with cv.at(x, y, 1, a):
                cv.poly([(-q, -q), (q, -q), (q, q), (-q, q)], True, "hair", ctx["zg"], ctx["tags"])
        elif frame == "diamond":
            q = h * 0.7
            with cv.at(x, y, 1, a):
                cv.poly([(0, -q), (q, 0), (0, q), (-q, 0)], True, "hair", ctx["zg"], ctx["tags"])
        size = h * (0.62 if frame != "none" else 0.9)
        if text:
            script.draw_glyph(cv, g, x, y, size, rot, "thin", ctx["zg"], ctx["tags"])
        else:
            script.draw_glyph(cv, g, x, y, size * 1.05, rot, "thin", ctx["zg"], ctx["tags"])


def b_roundels(cv, b, ctx):
    m = b["m"]
    rm = (b["ri"] + b["ro"]) / 2
    rr = (b["ro"] - b["ri"]) / 2 * b.get("size", 0.95)
    content = b.get("content", "script")
    first = None
    for a in _positions(m, ctx["phase"] + b.get("phase", 0), ctx["avoid"], 360 / m / 3):
        x, y = polar(rm, a)
        cv.circle(rr, x, y, tier="thin", z=ctx["zg"], tags=ctx["tags"])
        cv.clear_disc(rr * 1.12, x, y, z=ctx["zc"] - 0.5)
        if b.get("double"):
            cv.circle(rr * 0.8, x, y, tier="hair", z=ctx["zg"], tags=ctx["tags"])
        inner = rr * (0.62 if b.get("double") else 0.75)
        if content == "dot":
            cv.dot(rr * 0.22, x, y, z=ctx["zg"], tags=ctx["tags"])
        elif content == "bullseye":
            cv.circle(rr * 0.45, x, y, tier="hair", z=ctx["zg"], tags=ctx["tags"])
            cv.dot(rr * 0.15, x, y, z=ctx["zg"], tags=ctx["tags"])
        elif content != "none":
            if b.get("fixed") and first is not None:
                g, text = first
            else:
                g, text = _symbol_for(content, ctx, int(round((a - ctx["phase"]) / (360 / m))) % m)
                first = (g, text)
            script.draw_glyph(cv, g, x, y, inner * (1.05 if text else 1.25), a, "thin", ctx["zg"], ctx["tags"])


def b_ticks(cv, b, ctx):
    m, j = b["m"], b.get("major", 0)
    side = b.get("side", "in")
    L = b["ro"] - b["ri"]
    for i in range(m):
        a = ctx["phase"] + i * 360.0 / m
        if not _free(ctx["avoid"], a):
            continue
        major = j and i % j == 0
        ln = L if major else L * b.get("minor", 0.5)
        if side == "in":
            r0, r1 = b["ro"] - ln, b["ro"]
        elif side == "out":
            r0, r1 = b["ri"], b["ri"] + ln
        else:
            mid = (b["ri"] + b["ro"]) / 2
            r0, r1 = mid - ln / 2, mid + ln / 2
        cv.line(polar(r0, a), polar(r1, a), "thin" if major else "hair", ctx["zb"], ctx["tags"])


def b_dots(cv, b, ctx):
    m = b["m"]
    rm = (b["ri"] + b["ro"]) / 2
    dr = (b["ro"] - b["ri"]) * b.get("size", 0.25)
    j = b.get("major", 0)
    hollow = b.get("hollow", False)
    for i in range(m):
        a = ctx["phase"] + i * 360.0 / m
        if not _free(ctx["avoid"], a):
            continue
        x, y = polar(rm, a)
        r = dr * (1.7 if j and i % j == 0 else 1.0)
        if hollow and not (j and i % j == 0):
            cv.circle(r, x, y, tier="hair", z=ctx["zb"], tags=ctx["tags"])
        else:
            cv.dot(r, x, y, z=ctx["zb"], tags=ctx["tags"])


def b_beads(cv, b, ctx):
    rm = (b["ri"] + b["ro"]) / 2
    rb = (b["ro"] - b["ri"]) / 2
    m = b["m"]
    rb = min(rb, math.pi * rm / m * 0.98)
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        x, y = polar(rm, a)
        cv.circle(rb, x, y, tier="hair", z=ctx["zb"], tags=ctx["tags"])


def b_loops(cv, b, ctx):
    """Chain of overlapping circles centred on the band's mid radius."""
    rm = (b["ri"] + b["ro"]) / 2
    rb = (b["ro"] - b["ri"]) / 2
    for a in _positions(b["m"], ctx["phase"], ctx["avoid"]):
        x, y = polar(rm, a)
        cv.circle(rb, x, y, tier="hair", z=ctx["zb"], tags=ctx["tags"])


def _polar_path(fn, a0, a1, n):
    """fn(t in 0..1) -> (angle offset in [0, 1] of the period, radius) sampled into a polyline."""
    t = np.linspace(0, 1, n)
    return [polar(r, a0 + (a1 - a0) * u) for u, r in (fn(x) for x in t)]


def b_zigzag(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    pts = []
    for i in range(2 * m + 1):
        a = ctx["phase"] + i * 180.0 / m
        pts.append(polar(ro if i % 2 == 0 else ri, a))
    cv.poly(pts[:-1], True, b.get("tier", "hair"), ctx["zb"], ctx["tags"])
    if b.get("fill"):                                   # alternate filled triangles (truss)
        for i in range(0, 2 * m, 2):
            a0 = ctx["phase"] + i * 180.0 / m
            tri = [polar(ro, a0), polar(ri, a0 + 180.0 / m), polar(ro, a0 + 360.0 / m)]
            if i % 4 == 0:
                cv.poly(tri, True, 0.0, ctx["zb"], ctx["tags"], fill=True)


def b_chevrons(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    w = 360.0 / m * 0.45
    d = 1 if b.get("dir", 1) > 0 else -1
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        cv.poly([polar(ro, a - w * d / 2), polar((ri + ro) / 2, a + w * d / 2), polar(ri, a - w * d / 2)], False,
                "hair", ctx["zb"], ctx["tags"])


def b_wave(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    rm, amp = (ri + ro) / 2, (ro - ri) / 2
    strands = b.get("strands", 1)
    uid = ctx["uid"]()
    paths = []
    for k in range(strands):
        ph = k * math.pi / strands * (2 if strands > 2 else 1)
        t = np.linspace(0, 2 * np.pi, m * 40, endpoint=False)
        a = ctx["phase"] + np.degrees(t)
        r = rm + amp * np.sin(m * t + ph)
        P = np.column_stack([r * np.sin(np.radians(a)), r * np.cos(np.radians(a))])
        tag = f"{uid}s{k}"
        cv.poly(P, True, b.get("tier", "hair"), ctx["zb"], (*ctx["tags"], tag))
        paths.append((P, tag))
    if strands == 2 and b.get("weave", True):            # braid: alternate over / under at the crossings
        for i in range(2 * m):
            th = (i * math.pi) / m
            a = ctx["phase"] + math.degrees(th)
            x, y = polar(rm, a)
            under = paths[i % 2][1]
            cv.clear_disc(amp * 0.28 + ctx["W"]["hair"] * 2 / ctx["s"], x, y, z=ctx["zb"] + 0.2, only=[under])


def b_crenel(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    pts = []
    step = 360.0 / m
    for i in range(m):
        a = ctx["phase"] + i * step
        pts += [polar(ri, a), polar(ro, a), polar(ro, a + step / 2), polar(ri, a + step / 2)]
    cv.poly(pts, True, "hair", ctx["zb"], ctx["tags"])


def b_meander(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    H = ro - ri
    step = 360.0 / m
    # one Greek-key unit in (u along 0..1, v radial 0..1)
    unit = [(0, 0), (0, 1), (0.75, 1), (0.75, 0.25), (0.35, 0.25), (0.35, 0.6), (0.5, 0.6)]
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        pts = []
        for u, v in unit:
            pts.append(polar(ri + v * H, a + u * step))
        cv.poly(pts, False, "hair", ctx["zb"], ctx["tags"])
        cv.line(polar(ri, a), polar(ri, a + step), "hair", ctx["zb"], ctx["tags"])


def b_scallop(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    step = 360.0 / m
    out = b.get("out", True)
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        t = np.linspace(0, 1, 24)
        base, peak = (ri, ro) if out else (ro, ri)
        P = [polar(base + (peak - base) * math.sin(math.pi * u), a + u * step) for u in t]
        cv.poly(P, False, "thin" if b.get("bold") else "hair", ctx["zb"], ctx["tags"])


def b_cells(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    step = 360.0 / m
    for i in range(m):
        a = ctx["phase"] + i * step
        if _free(ctx["avoid"], a):
            cv.line(polar(ri, a), polar(ro, a), "hair", ctx["zb"], ctx["tags"])
    sub = dict(b, kind="glyphs", phase=step / 2, size=b.get("size", 0.55), frame="none")
    b_glyphs(cv, sub, ctx)


def b_orbit(cv, b, ctx):
    rm = (b["ri"] + b["ro"]) / 2
    cv.circle(rm, tier="hair", z=ctx["zb"], tags=ctx["tags"])
    rb = (b["ro"] - b["ri"]) / 2
    rng = ctx["rng"]
    k = b.get("m", 3)
    angles = ([ctx["phase"] + i * 360 / k for i in range(k)] if b.get("sym", True)
              else [rng.uniform(0, 360) for _ in range(k)])
    for a in angles:
        if not _free(ctx["avoid"], a, 6):
            continue
        x, y = polar(rm, a)
        size = rb * rng.choice([0.5, 0.7, 1.0]) if not b.get("sym", True) else rb * 0.7
        if b.get("body", "ring") == "dot":
            cv.dot(size * 0.6, x, y, z=ctx["zg"], tags=ctx["tags"])
        else:
            cv.circle(size, x, y, tier="hair", z=ctx["zg"], tags=ctx["tags"])
            cv.dot(size * 0.3, x, y, z=ctx["zg"], tags=ctx["tags"])
            cv.clear_disc(size * 1.25, x, y, z=ctx["zb"] + 0.3, only=ctx["tags"])


def b_arcs(cv, b, ctx):
    """Bold partial arcs: one long arc (asymmetric accent) or n arcs with gaps."""
    rm = (b["ri"] + b["ro"]) / 2
    w = (b["ro"] - b["ri"]) * ctx["s"]
    if b.get("single"):
        a0 = ctx["phase"] + b.get("start", 200)
        cv.arc(rm, a0, a0 + b.get("span", 220), tier=w, z=ctx["zb"], tags=ctx["tags"])
    else:
        m = b["m"]
        gap = b.get("gapdeg", 12)
        for i in range(m):
            a = ctx["phase"] + i * 360 / m + gap / 2
            cv.arc(rm, a, a + 360 / m - gap, tier=w, z=ctx["zb"], tags=ctx["tags"])


def b_gear(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    step = 360.0 / m
    pts = []
    for i in range(m):
        a = ctx["phase"] + i * step
        pts += [polar(ri, a), polar(ro, a + step * 0.15), polar(ro, a + step * 0.45), polar(ri, a + step * 0.6)]
    cv.poly(pts, True, "thin", ctx["zb"], ctx["tags"])


def b_petals(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    step = 360.0 / m
    layers = b.get("layers", 1)
    for L in range(layers):
        ph = ctx["phase"] + L * step / 2
        top = ro if L == 0 else ri + (ro - ri) * 0.7
        for a in _positions(m, ph, ctx["avoid"]):
            t = np.linspace(0, 1, 18)
            left = [polar(ri + (top - ri) * math.sin(u * math.pi / 2) ** 0.8, a - step / 2 * (1 - u)) for u in t]
            right = [polar(ri + (top - ri) * math.sin(u * math.pi / 2) ** 0.8, a + step / 2 * (1 - u)) for u in t]
            cv.poly(left + right[::-1], False, "hair", ctx["zb"], ctx["tags"])


def b_sparkles(cv, b, ctx):
    m = b["m"]
    rm = (b["ri"] + b["ro"]) / 2
    h = (b["ro"] - b["ri"]) * 0.9
    g = symbols.sparkle(b.get("k", 4), 0.13)
    for a in _positions(m, ctx["phase"] + b.get("phase", 0), ctx["avoid"]):
        x, y = polar(rm, a)
        script.draw_glyph(cv, g, x, y, h, a, "hair", ctx["zb"], ctx["tags"])


def b_diamonds(cv, b, ctx):
    """Chain of lozenges touching tip to tip (optionally with a dot inside)."""
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    rm = (ri + ro) / 2
    step = 360.0 / m
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        cv.poly([polar(rm, a - step / 2), polar(ro, a), polar(rm, a + step / 2), polar(ri, a)], True, "hair",
                ctx["zb"], ctx["tags"])
        if b.get("dot"):
            cv.dot((ro - ri) * 0.1, *polar(rm, a), z=ctx["zb"], tags=ctx["tags"])


def b_crosses(cv, b, ctx):
    m = b["m"]
    rm = (b["ri"] + b["ro"]) / 2
    h = (b["ro"] - b["ri"]) * 0.42
    kind = b.get("style", "plain")
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        with cv.at(*polar(rm, a), 1, a):
            cv.line((0, -h), (0, h), "hair", ctx["zb"], ctx["tags"])
            y = h * 0.3 if kind == "latin" else 0.0
            cv.line((-h * 0.6, y), (h * 0.6, y), "hair", ctx["zb"], ctx["tags"])
            if kind == "double":
                cv.line((-h * 0.4, -h * 0.45), (h * 0.4, -h * 0.45), "hair", ctx["zb"], ctx["tags"])


def b_ladder(cv, b, ctx):
    """Two rails with rungs (the 'ladder' band of Cardcaptor-like circles)."""
    ri, ro = b["ri"], b["ro"]
    cv.circle(ri, tier="hair", z=ctx["zb"], tags=ctx["tags"])
    cv.circle(ro, tier="hair", z=ctx["zb"], tags=ctx["tags"])
    for a in _positions(b["m"], ctx["phase"], ctx["avoid"]):
        cv.line(polar(ri, a), polar(ro, a), "hair", ctx["zb"], ctx["tags"])


def b_triangles(cv, b, ctx):
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    w = 360.0 / m * b.get("width", 0.4)
    out = b.get("out", True)
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        base, tip = (ri, ro) if out else (ro, ri)
        tri = [polar(base, a - w / 2), polar(tip, a), polar(base, a + w / 2)]
        cv.poly(tri, True, 0.0 if b.get("fill") else "hair", ctx["zb"], ctx["tags"], fill=bool(b.get("fill")))


def b_stars(cv, b, ctx):
    m = b["m"]
    rm = (b["ri"] + b["ro"]) / 2
    h = (b["ro"] - b["ri"]) * 0.85
    g = symbols.star(b.get("k", 5), 2)
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        script.draw_glyph(cv, g, *polar(rm, a), h, a, "hair", ctx["zb"], ctx["tags"])


def b_hatch(cv, b, ctx):
    """Dense slanted hatching (a woven / engraved texture)."""
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    sl = 360.0 / m * b.get("slant", 1.5)
    for i in range(m):
        a = ctx["phase"] + i * 360.0 / m
        if _free(ctx["avoid"], a):
            cv.line(polar(ri, a), polar(ro, a + sl), "hair", ctx["zb"], ctx["tags"])
            if b.get("cross"):
                cv.line(polar(ri, a + sl), polar(ro, a), "hair", ctx["zb"], ctx["tags"])


def b_vesica(cv, b, ctx):
    """Chain of lens shapes lying along the band."""
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    rm = (ri + ro) / 2
    amp = (ro - ri) / 2 * 0.9
    step = 360.0 / m
    for a in _positions(m, ctx["phase"], ctx["avoid"]):
        t = np.linspace(0, 1, 18)
        up = [polar(rm + amp * math.sin(math.pi * u), a - step / 2 + u * step) for u in t]
        dn = [polar(rm - amp * math.sin(math.pi * u), a - step / 2 + u * step) for u in t]
        cv.poly(up + dn[::-1], True, "hair", ctx["zb"], ctx["tags"])


def b_keys(cv, b, ctx):
    """Alternating T-bars pointing out and in (a 'key' fret)."""
    m = b["m"]
    ri, ro = b["ri"], b["ro"]
    w = 360.0 / m * 0.3
    for i, a in enumerate(_positions(m, ctx["phase"], ctx["avoid"])):
        base, tip = (ri, ro) if i % 2 == 0 else (ro, ri)
        cv.line(polar(base, a), polar(tip, a), "hair", ctx["zb"], ctx["tags"])
        cv.line(polar(tip, a - w), polar(tip, a + w), "hair", ctx["zb"], ctx["tags"])


def b_empty(cv, b, ctx):
    pass


BANDS = {"text": b_text, "inverted": b_inverted, "glyphs": b_glyphs, "roundels": b_roundels, "ticks": b_ticks,
         "dots": b_dots, "beads": b_beads, "loops": b_loops, "zigzag": b_zigzag, "chevrons": b_chevrons,
         "wave": b_wave, "crenel": b_crenel, "meander": b_meander, "scallop": b_scallop, "cells": b_cells,
         "orbit": b_orbit, "arcs": b_arcs, "gear": b_gear, "petals": b_petals, "sparkles": b_sparkles,
         "empty": b_empty, "diamonds": b_diamonds, "crosses": b_crosses, "ladder": b_ladder,
         "triangles": b_triangles, "stars": b_stars, "hatch": b_hatch, "vesica": b_vesica, "keys": b_keys}


def band(cv, b, ctx):
    BANDS[b["kind"]](cv, b, ctx)
