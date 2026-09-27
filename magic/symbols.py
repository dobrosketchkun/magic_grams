"""Node / centre symbols in glyph format ({"s": polylines, "c": circles, "w": 1}, unit box, y up).

Generated families (unlimited):
  alchem   alchemical grammar: base (circle, triangle, square, crescent...) + top / bottom / through modifiers
  seal     Goetia-style mirrored line glyph: spine + symmetric limbs + terminal family (research/traditions §1b)
  trigram / hexagram (Yijing bits), geomantic (4 rows of 1-2 dots), sparkle, eye, sun, moon, star, bullseye
Harvested: lib:<set> (planets and zodiac from Hershey, Noto alchemical, Hershey misc marks) via library.node_set.
"""
from __future__ import annotations

import math
import random

import numpy as np


def _circ(cx, cy, r, n=None):
    n = n or 40
    t = np.linspace(0, 2 * np.pi, n + 1)
    return [(cx + r * math.sin(a), cy + r * math.cos(a)) for a in t]


def _arc(cx, cy, r, a0, a1, n=24):
    t = np.radians(np.linspace(a0, a1, n))
    return [(cx + r * math.sin(a), cy + r * math.cos(a)) for a in t]


def normalize(g, pad=0.0):
    """Scale / centre a glyph into the unit box keeping its aspect."""
    pts = [p for s in g["s"] for p in s] + [(x + dx * r, y + dy * r) for x, y, r, _ in g["c"]
                                             for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
    if not pts:
        return g
    P = np.asarray(pts, float)
    x0, y0 = P.min(0)
    x1, y1 = P.max(0)
    ext = max(x1 - x0, y1 - y0, 1e-6) * (1 + pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    f = lambda x, y: ((x - cx) / ext + 0.5, (y - cy) / ext + 0.5)
    return {"s": [[f(x, y) for x, y in s] for s in g["s"]],
            "c": [(*f(x, y), r / ext, fl) for x, y, r, fl in g["c"]], "w": 1.0}


# ---------------------------------------------------------------- alchemical grammar

def alchem(rng: random.Random) -> dict:
    s, c = [], []
    base = rng.choice(["circle", "circle", "tri_up", "tri_down", "square", "crescent", "diamond", "cross", "circle2"])
    cx, cy, r = 0.5, 0.5, 0.22
    top_y, bot_y = cy + r, cy - r
    if base == "circle":
        c.append((cx, cy, r, False))
    elif base == "circle2":
        c.append((cx, cy, r, False))
        c.append((cx, cy, r * 0.35, rng.random() < 0.5))
    elif base == "tri_up":
        s.append([(cx - r * 1.1, cy - r * 0.8), (cx + r * 1.1, cy - r * 0.8), (cx, cy + r * 1.1), (cx - r * 1.1, cy - r * 0.8)])
        top_y, bot_y = cy + r * 1.1, cy - r * 0.8
    elif base == "tri_down":
        s.append([(cx - r * 1.1, cy + r * 0.8), (cx + r * 1.1, cy + r * 0.8), (cx, cy - r * 1.1), (cx - r * 1.1, cy + r * 0.8)])
        top_y, bot_y = cy + r * 0.8, cy - r * 1.1
    elif base == "square":
        s.append([(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r), (cx - r, cy - r)])
    elif base == "diamond":
        s.append([(cx, cy - r * 1.2), (cx + r, cy), (cx, cy + r * 1.2), (cx - r, cy), (cx, cy - r * 1.2)])
        top_y, bot_y = cy + r * 1.2, cy - r * 1.2
    elif base == "crescent":
        s.append(_arc(cx, cy, r, 200, 520))
        s.append(_arc(cx + r * 0.45, cy, r * 0.8, 230, 490))
    elif base == "cross":
        s.append([(cx, cy - r), (cx, cy + r)])
        s.append([(cx - r, cy), (cx + r, cy)])
    through = rng.choice(["none", "none", "hbar", "vbar", "dot", "cross"])
    if through == "hbar":
        s.append([(cx - r * 1.3, cy), (cx + r * 1.3, cy)])
    elif through == "vbar":
        s.append([(cx, bot_y - 0.05), (cx, top_y + 0.05)])
    elif through == "dot" and base not in ("cross",):
        c.append((cx, cy, 0.03, True))
    elif through == "cross" and base in ("circle", "circle2", "square"):
        s.append([(cx - r, cy), (cx + r, cy)])
        s.append([(cx, cy - r), (cx, cy + r)])
    top = rng.choice(["none", "none", "horns", "cross", "arrow", "circle", "bar"])
    if top == "horns":
        s.append(_arc(cx, top_y + 0.12, 0.13, 100, 260))
    elif top == "cross":
        s.append([(cx, top_y), (cx, top_y + 0.22)])
        s.append([(cx - 0.08, top_y + 0.13), (cx + 0.08, top_y + 0.13)])
    elif top == "arrow":
        tx, ty = cx + 0.24, top_y + 0.16
        s.append([(cx + r * 0.7, cy + r * 0.7), (tx, ty)])
        s.append([(tx - 0.09, ty), (tx, ty), (tx, ty - 0.09)])
    elif top == "circle":
        c.append((cx, top_y + 0.08, 0.08, False))
    elif top == "bar":
        s.append([(cx - r, top_y + 0.07), (cx + r, top_y + 0.07)])
    bottom = rng.choice(["none", "none", "cross", "cross", "circle", "hook", "bar"])
    if bottom == "cross":
        s.append([(cx, bot_y), (cx, bot_y - 0.24)])
        s.append([(cx - 0.09, bot_y - 0.13), (cx + 0.09, bot_y - 0.13)])
    elif bottom == "circle":
        s.append([(cx, bot_y), (cx, bot_y - 0.08)])
        c.append((cx, bot_y - 0.15, 0.07, False))
    elif bottom == "hook":
        s.append([(cx, bot_y), (cx, bot_y - 0.18)] + _arc(cx + 0.07, bot_y - 0.18, 0.07, 270, 90))
    elif bottom == "bar":
        s.append([(cx - r, bot_y - 0.07), (cx + r, bot_y - 0.07)])
    return normalize({"s": s, "c": c, "w": 1.0})


# ---------------------------------------------------------------- Goetia-style seal glyph

TERMS = ["circle", "circle", "bar", "cross", "cup", "arrow", "fork", "dot", "curl"]


def _terminal(kind, p, d, size, s, c):
    """Terminal at point p, stroke direction d (unit, pointing outward)."""
    x, y = p
    nx, ny = -d[1], d[0]
    if kind == "circle":
        c.append((x + d[0] * size, y + d[1] * size, size, False))
    elif kind == "dot":
        c.append((x, y, size * 0.6, True))
    elif kind == "bar":
        s.append([(x - nx * size * 1.3, y - ny * size * 1.3), (x + nx * size * 1.3, y + ny * size * 1.3)])
    elif kind == "cross":
        q = (x + d[0] * size * 1.2, y + d[1] * size * 1.2)
        s.append([p, q])
        s.append([(q[0] - nx * size, q[1] - ny * size - 0), (q[0] + nx * size, q[1] + ny * size)])
    elif kind == "cup":
        a = math.degrees(math.atan2(d[0], d[1]))
        s.append(_arc(x + d[0] * size, y + d[1] * size, size, a + 90, a + 270, 16))
    elif kind == "arrow":
        s.append([(x - d[0] * size + nx * size, y - d[1] * size + ny * size), p,
                  (x - d[0] * size - nx * size, y - d[1] * size - ny * size)])
    elif kind == "fork":
        for k in (-1, 1):
            s.append([p, (x + d[0] * size * 1.2 + nx * size * k, y + d[1] * size * 1.2 + ny * size * k)])
        s.append([p, (x + d[0] * size * 1.4, y + d[1] * size * 1.4)])
    elif kind == "curl":
        a = math.degrees(math.atan2(d[0], d[1]))
        s.append(_arc(x + nx * size, y + ny * size, size, a - 90, a + 150, 16))


def seal_meta(gseed: int) -> str:
    """Coarse visible structure of seal(Random(gseed)): spine, limb kinds, terminal families."""
    return seal(random.Random(gseed))["meta"]


def seal(rng: random.Random, mirror=True) -> dict:
    s, c = [], []
    kinds = []
    ends = []                                      # (point, outward dir) of free ends on the right half (+ mirror)
    top, bot = rng.uniform(0.75, 0.95), rng.uniform(0.05, 0.3)
    spine = rng.random() < 0.8
    if spine:
        s.append([(0.5, bot), (0.5, top)])
        ends += [((0.5, top), (0, 1)), ((0.5, bot), (0, -1))]
    nl = rng.randint(1, 3)
    for _ in range(nl):
        y0 = rng.uniform(bot + 0.1, top - 0.05) if spine else rng.uniform(0.3, 0.7)
        kind = rng.choice(["straight", "bent", "bent", "hbar", "diag"])
        kinds.append(kind[0])
        if kind == "hbar":
            x1 = rng.uniform(0.72, 0.95)
            s.append([(0.5, y0), (x1, y0)])
            ends.append(((x1, y0), (1, 0)))
        elif kind == "straight" or kind == "diag":
            x1, y1 = rng.uniform(0.7, 0.95), y0 + rng.uniform(-0.3, 0.3)
            s.append([(0.5, y0), (x1, y1)])
            L = math.hypot(x1 - 0.5, y1 - y0) or 1
            ends.append(((x1, y1), ((x1 - 0.5) / L, (y1 - y0) / L)))
        else:
            x1, y1 = rng.uniform(0.62, 0.82), y0 + rng.uniform(-0.2, 0.2)
            x2, y2 = x1 + rng.uniform(-0.05, 0.12), y1 + rng.choice([-1, 1]) * rng.uniform(0.12, 0.28)
            s.append([(0.5, y0), (x1, y1), (x2, y2)])
            L = math.hypot(x2 - x1, y2 - y1) or 1
            ends.append(((x2, y2), ((x2 - x1) / L, (y2 - y1) / L)))
    if rng.random() < 0.35:                       # central lozenge / ring
        yc = rng.uniform(0.4, 0.6)
        if rng.random() < 0.5:
            s.append([(0.5, yc - 0.12), (0.6, yc), (0.5, yc + 0.12), (0.4, yc), (0.5, yc - 0.12)])
        else:
            c.append((0.5, yc, 0.08, False))
    for _ in range(rng.choice([0, 0, 1, 2])):     # ticks threaded on the spine
        if spine:
            y = rng.uniform(bot + 0.05, top - 0.05)
            s.append([(0.43, y), (0.57, y)])
    fam = rng.sample(TERMS, 2)
    right = [e for e in ends if e[0][0] > 0.5 + 1e-6]
    centre = [e for e in ends if abs(e[0][0] - 0.5) < 1e-6]
    for (p, d) in centre:
        _terminal(fam[0] if rng.random() < 0.7 else fam[1], p, d, 0.055, s, c)
    for (p, d) in right:
        _terminal(rng.choice(fam), p, d, 0.05, s, c)
    if mirror:                                     # reflect every right-side piece to the left
        ms = [[(1 - x, y) for x, y in q] for q in s if any(x > 0.5 + 1e-6 for x, _ in q)]
        mc = [(1 - x, y, r, f) for x, y, r, f in c if x > 0.5 + 1e-6]
        s += ms
        c += mc
    g = normalize({"s": s, "c": c, "w": 1.0})
    g["meta"] = ("s" if spine else "n") + "".join(sorted(kinds)) + ":" + "-".join(sorted(fam))
    return g


# ---------------------------------------------------------------- small families

def trigram(bits) -> dict:
    s = []
    n = len(bits)
    for i, b in enumerate(bits):
        y = 0.5 + (i - (n - 1) / 2) * (0.8 / max(n - 1, 1)) * (0.9 if n > 3 else 1)
        if b:
            s.append([(0.1, y), (0.9, y)])
        else:
            s.append([(0.1, y), (0.42, y)])
            s.append([(0.58, y), (0.9, y)])
    return {"s": s, "c": [], "w": 1.0}


def geomantic(rows) -> dict:
    c = []
    for i, k in enumerate(rows):
        y = 0.85 - i * 0.23
        xs = [0.5] if k == 1 else [0.35, 0.65]
        c += [(x, y, 0.06, True) for x in xs]
    return {"s": [], "c": c, "w": 1.0}


def sparkle(k=4, inner=0.12) -> dict:
    pts = []
    for i in range(2 * k):
        r = 0.5 if i % 2 == 0 else inner
        a = math.radians(i * 180 / k)
        pts.append((0.5 + r * math.sin(a), 0.5 + r * math.cos(a)))
    pts.append(pts[0])
    return {"s": [pts], "c": [], "w": 1.0}


def star(n=5, k=2) -> dict:
    V = [(0.5 + 0.48 * math.sin(math.radians(i * 360 / n)), 0.5 + 0.48 * math.cos(math.radians(i * 360 / n))) for i in range(n)]
    s = []
    g = math.gcd(n, k)
    for start in range(g):
        path, i = [], start
        for _ in range(n // g + 1):
            path.append(V[i])
            i = (i + k) % n
        s.append(path)
    return {"s": s, "c": [], "w": 1.0}


def eye() -> dict:
    up = _arc(0.5, -0.25, 0.75, -48, 48)
    lo = _arc(0.5, 1.25, 0.75, 132, 228)
    return {"s": [up, lo], "c": [(0.5, 0.5, 0.14, False), (0.5, 0.5, 0.05, True)], "w": 1.0}


def sun(rays=8) -> dict:
    s = []
    for i in range(rays):
        a = math.radians(i * 360 / rays)
        s.append([(0.5 + 0.28 * math.sin(a), 0.5 + 0.28 * math.cos(a)), (0.5 + 0.48 * math.sin(a), 0.5 + 0.48 * math.cos(a))])
    return {"s": s, "c": [(0.5, 0.5, 0.2, False), (0.5, 0.5, 0.05, True)], "w": 1.0}


def moon() -> dict:
    return {"s": [_arc(0.5, 0.5, 0.42, 200, 520), _arc(0.66, 0.55, 0.34, 225, 495)], "c": [], "w": 1.0}


def bullseye(k=2) -> dict:
    return {"s": [], "c": [(0.5, 0.5, 0.45 * (1 - i / (k + 0.5)), False) for i in range(k)] + [(0.5, 0.5, 0.06, True)],
            "w": 1.0}


FAMILIES = ["alchem", "seal", "lib:hershey_astro", "lib:alchemical", "trigram", "geomantic", "sparkle", "star",
            "eye", "sun", "moon", "bullseye", "lib:hershey_misc", "script"]


def symbol(kind: str, rng: random.Random, alpha=None) -> dict:
    if kind == "alchem":
        return alchem(rng)
    if kind == "seal":
        return seal(rng)
    if kind.startswith("lib:"):
        from .library import node_set
        return rng.choice(node_set(kind[4:]))
    if kind == "trigram":
        return trigram([rng.random() < 0.5 for _ in range(3)])
    if kind == "hexagram":
        return trigram([rng.random() < 0.5 for _ in range(6)])
    if kind == "geomantic":
        return geomantic([rng.choice([1, 2]) for _ in range(4)])
    if kind == "sparkle":
        return sparkle(rng.choice([4, 4, 8]), rng.choice([0.08, 0.14]))
    if kind == "star":
        n = rng.choice([5, 6, 7, 8])
        return star(n, 2 if n < 7 else 3)
    if kind == "eye":
        return eye()
    if kind == "sun":
        return sun(rng.choice([8, 12]))
    if kind == "moon":
        return moon()
    if kind == "bullseye":
        return bullseye(rng.choice([1, 2]))
    if kind == "script" and alpha:
        g = rng.choice(alpha)
        return normalize({"s": [list(map(tuple, q)) for q in g["s"]], "c": list(g.get("c", [])), "w": 1.0})
    return alchem(rng)
