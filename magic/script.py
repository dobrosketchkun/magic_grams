"""Scripts: invented alphabets (one genome per circle) and harvested ones, laid out on arcs.

A glyph is {"s": [polyline, ...], "c": [(x, y, r, filled), ...], "w": width} in glyph space: baseline y=0, cap
height y=1, x from 0 to w. `c` holds ring / dot terminals.

Invented alphabets follow what makes real scripts look coherent (research/symbols.md §5): one lattice, one small
stroke vocabulary, one terminal style, similar stroke counts, and a minimum distance between glyphs (mirror images
count as the same glyph). Styles:
  rune     straight strokes on a stave (futhark-like)          ring    lattice strokes with ring terminals (Malachim)
  block    orthogonal maze strokes (Frieren-like)                curl    smooth hooks and loops
  angular  one bent main stroke + hook (Theban/Enochian feel)    cursive connected hand, glyphs join on a baseline
  cell     pigpen-like cell corners with dots                    lib:<set> a harvested alphabet (see library.py)
"""
from __future__ import annotations

import math
import random

import numpy as np

from .canvas import densify

STYLES = {"rune": 5, "ring": 5, "block": 3, "curl": 3, "angular": 4, "cursive": 1.4, "cell": 1.4}
TERMINALS = ["none", "ring", "dot", "bar"]


def catmull(points, n=8):
    """Smooth curve through points (Catmull-Rom)."""
    P = np.asarray(points, float)
    if len(P) < 3:
        return P
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def _key(glyph, mirror=False):
    w = glyph["w"] or 1
    segs = []
    for s in glyph["s"]:
        pts = [((w - x) if mirror else x, y) for x, y in np.asarray(s)[:: max(1, len(s) // 6)]]
        pts.append(((w - s[-1][0]) if mirror else s[-1][0], s[-1][1]))
        q = tuple((round(x / w * 4), round(y * 4)) for x, y in pts)
        segs.append(min(q, q[::-1]))
    return tuple(sorted(segs))


# ---------------------------------------------------------------- invented glyph styles

def _lattice(cols, rows, w):
    return [(w * i / (cols - 1), j / (rows - 1)) for j in range(rows) for i in range(cols)]


def _g_rune(rng, gen):
    w = gen["w"]
    rows = gen["rows"]
    xs = [0.0, w / 2, w]
    ys = [j / (rows - 1) for j in range(rows)]
    strokes = []
    staves = rng.choices([1, 2, 0], [7, 2, 1])[0]
    stave_x = [xs[rng.choice([0, 1])]] if staves == 1 else ([xs[0], xs[2]] if staves == 2 else [])
    for x in stave_x:
        strokes.append([(x, 0.0), (x, 1.0)])
    nb = rng.randint(gen["smin"], gen["smax"])
    for _ in range(nb):
        if stave_x:
            x0 = rng.choice(stave_x)
            y0 = rng.choice(ys[1:] if rng.random() < 0.8 else ys)
        else:
            x0, y0 = rng.choice(xs), rng.choice(ys)
        x1 = rng.choice([x for x in xs if abs(x - x0) > 1e-9])
        y1 = min(ys, key=lambda y: abs(y - (y0 + rng.choice([-1, -0.5, 0, 0.5, 1]) * (1.0 / (rows - 1)) * rng.choice([1, 2]))))
        if (x1, y1) == (x0, y0):
            continue
        strokes.append([(x0, y0), (x1, y1)])
    return {"s": strokes, "c": [], "w": w}


def _graph_glyph(rng, gen, pts_pool, nseg):
    """Connected random segments on a lattice (shared by ring / cell styles)."""
    start = rng.choice(pts_pool)
    nodes = [start]
    strokes = []
    for _ in range(nseg):
        a = rng.choice(nodes)
        cand = [p for p in pts_pool if p != a and math.dist(p, a) <= gen["reach"] + 1e-9]
        if not cand:
            continue
        b = rng.choice(cand)
        if any({tuple(a), tuple(b)} == {tuple(s[0]), tuple(s[-1])} for s in strokes):
            continue
        strokes.append([a, b])
        nodes.append(b)
    return strokes


def _ends(strokes):
    deg = {}
    for s in strokes:
        for p in (tuple(s[0]), tuple(s[-1])):
            deg[p] = deg.get(p, 0) + 1
    return [p for p, d in deg.items() if d == 1]


def _terminals(rng, gen, strokes):
    c = []
    if gen["term"] == "none":
        return c, strokes
    extra = []
    for p in _ends(strokes):
        if rng.random() < gen["p_term"]:
            if gen["term"] == "ring":
                c.append((p[0], p[1], 0.085, False))
            elif gen["term"] == "dot":
                c.append((p[0], p[1], 0.05, True))
            elif gen["term"] == "bar":
                # short bar perpendicular to the stroke end
                s = next(s for s in strokes if tuple(s[0]) == p or tuple(s[-1]) == p)
                q = s[1] if tuple(s[0]) == p else s[-2]
                dx, dy = p[0] - q[0], p[1] - q[1]
                L = math.hypot(dx, dy) or 1
                nx, ny = -dy / L * 0.09, dx / L * 0.09
                extra.append([(p[0] - nx, p[1] - ny), (p[0] + nx, p[1] + ny)])
    return c, strokes + extra


def _g_ring(rng, gen):
    w = gen["w"]
    pool = _lattice(3, 3, w)
    strokes = _graph_glyph(rng, gen, pool, rng.randint(gen["smin"], gen["smax"]))
    c, strokes = _terminals(rng, gen, strokes)
    return {"s": strokes, "c": c, "w": w}


def _g_block(rng, gen):
    w = gen["w"]
    n = 3
    grid = [(w * i / n, j / n) for i in range(n + 1) for j in range(n + 1)]
    strokes = []
    for _ in range(rng.randint(1, 2)):
        p = rng.choice(grid)
        path = [p]
        d = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        for _ in range(rng.randint(2, 5)):
            if rng.random() < 0.55:
                d = (d[1], d[0]) if rng.random() < 0.5 else (-d[1], -d[0])
            k = rng.choice([1, 1, 2])
            q = (p[0] + d[0] * k * w / n, p[1] + d[1] * k / n)
            if not (-1e-9 <= q[0] <= w + 1e-9 and -1e-9 <= q[1] <= 1 + 1e-9):
                d = (-d[0], -d[1])
                q = (p[0] + d[0] * w / n, p[1] + d[1] / n)
                if not (-1e-9 <= q[0] <= w + 1e-9 and -1e-9 <= q[1] <= 1 + 1e-9):
                    break
            path.append(q)
            p = q
        if len(path) >= 2:
            strokes.append(path)
    if rng.random() < 0.3:
        x, y = rng.choice([(w / 3, 1 / 3), (w / 3, 2 / 3), (2 * w / 3, 1 / 3)])
        s = 0.33
        strokes.append([(x, y), (x + s * w / 2, y), (x + s * w / 2, y + s / 2), (x, y + s / 2), (x, y)])
    return {"s": strokes, "c": [], "w": w}


def _g_curl(rng, gen):
    w = gen["w"]
    strokes = []
    c = []
    for _ in range(rng.randint(gen["smin"], max(gen["smin"], gen["smax"] - 1))):
        k = rng.randint(3, 4)
        pts = [(rng.uniform(0, w), rng.uniform(0, 1)) for _ in range(k)]
        if rng.random() < 0.5:                                    # hook / loop at the end
            x, y = pts[-1]
            r = 0.16
            a0 = rng.uniform(0, 2 * math.pi)
            pts += [(x + r * math.cos(a0 + t), y + r * math.sin(a0 + t)) for t in (1.5, 3.0, 4.5)]
        P = catmull(pts, 6)
        P[:, 0] = np.clip(P[:, 0], -0.1 * w, 1.1 * w)
        P[:, 1] = np.clip(P[:, 1], -0.1, 1.1)
        strokes.append([tuple(p) for p in P])
    if gen["term"] == "dot" and rng.random() < 0.5:
        c.append((rng.uniform(0.2, 0.8) * w, rng.choice([0.0, 1.0]), 0.05, True))
    return {"s": strokes, "c": c, "w": w}


def _g_angular(rng, gen):
    w = gen["w"]
    pool = _lattice(3, 4, w)
    k = rng.randint(3, 5)
    pts = [rng.choice(pool)]
    while len(pts) < k:
        q = rng.choice(pool)
        if q != pts[-1] and (len(pts) < 2 or q != pts[-2]):
            pts.append(q)
    strokes = [pts]
    x, y = pts[-1]
    px, py = pts[-2]
    dx, dy = x - px, y - py
    L = math.hypot(dx, dy) or 1
    if rng.random() < 0.7:                                        # hooked end
        hx, hy = -dy / L * 0.2, dx / L * 0.2
        strokes[0] = pts + [(x + hx + dx / L * 0.08, y + hy + dy / L * 0.08)]
    if rng.random() < gen["p_bar"]:
        a, b = rng.sample(pool, 2)
        strokes.append([a, b])
    c, strokes = _terminals(rng, gen, strokes)
    return {"s": strokes, "c": c, "w": w}


def _g_cursive(rng, gen):
    w = gen["w"]
    base = 0.25
    k = rng.randint(2, 3)
    pts = [(0.0, base)]
    for i in range(k):
        x = w * (i + 1) / (k + 1) + rng.uniform(-0.1, 0.1) * w
        y = rng.choice([0.0, 0.5, 1.0, 0.8])
        pts.append((x, y))
        if rng.random() < 0.3:                                   # loop
            pts.append((x - 0.15 * w, y - 0.25))
            pts.append((x + 0.05 * w, y - 0.1))
    pts.append((w, base))
    P = catmull(pts, 6)
    return {"s": [[tuple(p) for p in P]], "c": [], "w": w, "join": True}


def _g_cell(rng, gen):
    w = gen["w"]
    corners = [(0, 0), (w, 0), (w, 1), (0, 1)]
    edges = [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    kind = rng.choice(["L", "U", "box", "V", "V"])
    strokes = []
    if kind == "L":
        i = rng.randrange(4)
        strokes.append([edges[i][0], edges[i][1], edges[(i + 1) % 4][1]])
    elif kind == "U":
        i = rng.randrange(4)
        strokes.append([edges[i][0], edges[i][1], edges[(i + 1) % 4][1], edges[(i + 2) % 4][1]])
    elif kind == "box":
        strokes.append(corners + [corners[0]])
    else:
        a = rng.choice([((0, 1), (w / 2, 0), (w, 1)), ((0, 0), (w / 2, 1), (w, 0)), ((0, 0), (w, 0.5), (0, 1)),
                        ((w, 0), (0, 0.5), (w, 1))])
        strokes.append(list(a))
    c = []
    for _ in range(rng.choice([0, 1, 1, 2])):
        c.append((rng.choice([0.33, 0.5, 0.67]) * w, rng.choice([0.33, 0.5, 0.67]), 0.07, True))
    return {"s": strokes, "c": c, "w": w}


GEN = {"rune": _g_rune, "ring": _g_ring, "block": _g_block, "curl": _g_curl, "angular": _g_angular,
       "cursive": _g_cursive, "cell": _g_cell}


def genome(rng: random.Random, lib_sets=()) -> dict:
    """Script genome: the style choices shared by every glyph of one alphabet."""
    styles = dict(STYLES)
    for s in lib_sets:
        styles["lib:" + s] = 1.0
    style = rng.choices(list(styles), list(styles.values()))[0]
    g = {"style": style, "seed": rng.randrange(1 << 30)}
    if style.startswith("lib:"):
        return g
    g["w"] = {"rune": rng.choice([0.5, 0.6, 0.7]), "ring": rng.choice([0.7, 0.85, 1.0]),
              "block": rng.choice([0.8, 1.0]), "curl": rng.choice([0.6, 0.8]), "angular": rng.choice([0.6, 0.75]),
              "cursive": rng.choice([0.7, 0.9]), "cell": rng.choice([0.7, 0.9])}[style]
    g["rows"] = rng.choice([3, 4, 5])
    g["smin"], g["smax"] = rng.choice([(1, 2), (2, 3), (2, 4)])
    g["term"] = {"ring": rng.choice(["ring", "ring", "dot"]), "angular": rng.choice(TERMINALS),
                 "curl": rng.choice(["none", "dot"]), "rune": rng.choice(["none", "none", "dot", "bar"])}.get(style, "none")
    g["p_term"] = rng.choice([0.4, 0.7, 1.0])
    g["p_bar"] = rng.choice([0.0, 0.3, 0.6])
    g["reach"] = rng.choice([0.75, 1.2])
    g["sep"] = rng.choice(["dot", "dot", "diamond", "cross", "bar", "space", "ring"])
    g["size"] = rng.randint(18, 28)
    return g


def alphabet(gen: dict, library=None) -> list[dict]:
    rng = random.Random(gen["seed"])
    if gen["style"].startswith("lib:"):
        from .library import text_set
        return text_set(gen["style"][4:])
    fn = GEN[gen["style"]]
    out, keys = [], set()
    for _ in range(gen["size"] * 30):
        if len(out) >= gen["size"]:
            break
        g = fn(rng, gen)
        if not g["s"]:
            continue
        L = sum(np.linalg.norm(np.diff(np.asarray(s, float), axis=0), axis=1).sum() for s in g["s"])
        if L < 0.9 or L > 6.0:                   # too slight / too heavy
            continue
        k, km = _key(g), _key(g, True)
        if k in keys or km in keys:
            continue
        keys.add(k)
        out.append(g)
    return out


# ---------------------------------------------------------------- separators, numerals

def separator(kind: str) -> dict | None:
    if kind == "dot":
        return {"s": [], "c": [(0.12, 0.5, 0.07, True)], "w": 0.24}
    if kind == "diamond":
        return {"s": [[(0.0, 0.5), (0.15, 0.72), (0.3, 0.5), (0.15, 0.28), (0.0, 0.5)]], "c": [], "w": 0.3}
    if kind == "cross":
        return {"s": [[(0.2, 0.2), (0.2, 0.8)], [(0.0, 0.5), (0.4, 0.5)]], "c": [], "w": 0.4}
    if kind == "bar":
        return {"s": [[(0.08, 0.05), (0.08, 0.95)]], "c": [], "w": 0.16}
    if kind == "ring":
        return {"s": [], "c": [(0.14, 0.5, 0.12, False)], "w": 0.28}
    return None


def _letter(ch):
    """Roman numeral letters (clock rings)."""
    if ch == "I":
        return [[(0.12, 0), (0.12, 1)]], 0.24
    if ch == "V":
        return [[(0, 1), (0.3, 0), (0.6, 1)]], 0.6
    if ch == "X":
        return [[(0, 0), (0.6, 1)], [(0, 1), (0.6, 0)]], 0.6
    return [], 0.3


def roman(n: int) -> dict:
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    s = ""
    for v, t in vals:
        while n >= v:
            s += t
            n -= v
    strokes, x = [], 0.0
    for ch in s:
        st, w = _letter(ch)
        strokes += [[(px + x, py) for px, py in q] for q in st]
        x += w + 0.08
    return {"s": strokes, "c": [], "w": max(x - 0.08, 0.1)}


# ---------------------------------------------------------------- layout on arcs

def text_tokens(rng: random.Random, alpha: list[dict], sep: dict | None, count: int, word=(2, 6)):
    out = []
    while len(out) < count:
        for _ in range(rng.randint(*word)):
            out.append(rng.randrange(len(alpha)))
        if sep is not None:
            out.append(-1)
        else:
            out.append(-2)                        # plain space
    return out[:count]


def _map_glyph(g, h, r_base, s0, a_ref, sign, r_mid, inward):
    """Glyph -> arc: glyph x runs along the arc (arc length from s0), y is radial."""
    strokes = []
    for s in g["s"]:
        P = densify(np.asarray(s, float), False, 0.08)
        S = s0 + P[:, 0] * h
        a = a_ref + sign * np.degrees(S / r_mid)
        r = (r_base + h - P[:, 1] * h) if inward else (r_base + P[:, 1] * h)
        t = np.radians(a)
        strokes.append(np.column_stack([r * np.sin(t), r * np.cos(t)]))
    circles = []
    for x, y, rr, filled in g.get("c", []):
        S = s0 + x * h
        a = a_ref + sign * math.degrees(S / r_mid)
        r = (r_base + h - y * h) if inward else (r_base + y * h)
        t = math.radians(a)
        circles.append((r * math.sin(t), r * math.cos(t), rr * h, filled))
    return strokes, circles


def lay_arc(canvas, alpha, tokens, sep, r_in, r_out, a0, a1, fill=0.62, inward=False, tier="hair", z=4.0,
            tags=(), spacing=0.18, justify=True):
    """Lay glyph tokens along the band [r_in, r_out] between angles a0 < a1 (clockwise). Returns glyphs used."""
    band = r_out - r_in
    h = band * fill
    r_base = r_in + (band - h) / 2
    r_mid = r_base + h / 2
    L = math.radians(a1 - a0) * r_mid
    items = []
    used = 0.0
    for t in tokens:
        g = alpha[t] if t >= 0 else (sep if t == -1 else {"s": [], "c": [], "w": 0.35})
        if g is None:
            g = {"s": [], "c": [], "w": 0.35}
        adv = g["w"] * h + (0 if g.get("join") else spacing * h)
        if used + g["w"] * h > L:
            break
        items.append((g, used))
        used += adv
    while items and not items[-1][0]["s"] and not items[-1][0].get("c"):
        items.pop()
    if not items:
        return 0
    last_g, last_x = items[-1]
    content = last_x + last_g["w"] * h
    slack = L - content
    joined = bool(items[0][0].get("join"))
    stretch = (slack / max(len(items) - 1, 1)) if (justify and not joined) else 0.0
    offset = slack / 2 if (not justify or joined) else 0.0
    sign = -1 if inward else 1
    a_ref = a1 if inward else a0
    for i, (g, x) in enumerate(items):
        s0 = offset + x + stretch * i
        strokes, circles = _map_glyph(g, h, r_base, s0, a_ref, sign, r_mid, inward)
        for P in strokes:
            canvas.poly(P, False, tier, z, tags)
        for cx, cy, rr, filled in circles:
            if filled:
                canvas.dot(rr, cx, cy, z=z, tags=tags)
            else:
                canvas.circle(rr, cx, cy, tier, z, tags)
    return len(items)


def draw_glyph(canvas, g, cx, cy, size, rot=0.0, tier="thin", z=4.0, tags=(), centered_text=True):
    """Rigid glyph (not bent), centred at (cx, cy), cap height = size, rotated by rot (deg, clockwise)."""
    ox = g["w"] / 2 if centered_text else 0.0
    oy = 0.5 if centered_text else 0.0
    with canvas.at(cx, cy, size, rot):
        for s in g["s"]:
            P = np.asarray(s, float) - (ox, oy)
            canvas.poly(P, False, tier, z, tags)
        for x, y, rr, filled in g.get("c", []):
            if filled:
                canvas.dot(rr, x - ox, y - oy, z=z, tags=tags)
            else:
                canvas.circle(rr, x - ox, y - oy, tier, z, tags)


def lay_line(canvas, alpha, tokens, sep, p0, p1, height, tier="hair", z=4.0, tags=(), spacing=0.18):
    """Lay glyph tokens along the straight segment p0 -> p1 (glyph baseline on the segment's left side)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return 0
    u = d / L
    v = np.array([-u[1], u[0]])
    items, used = [], 0.0
    for t in tokens:
        g = alpha[t] if t >= 0 else (sep if t == -1 else {"s": [], "c": [], "w": 0.35})
        if g is None:
            g = {"s": [], "c": [], "w": 0.35}
        if used + g["w"] * height > L:
            break
        items.append((g, used))
        used += g["w"] * height + (0 if g.get("join") else spacing * height)
    if not items:
        return 0
    content = items[-1][1] + items[-1][0]["w"] * height
    stretch = (L - content) / max(len(items) - 1, 1)
    origin = p0 - v * height / 2
    for i, (g, x) in enumerate(items):
        s0 = x + stretch * i
        for s in g["s"]:
            P = np.asarray(s, float)
            Q = origin + np.outer(s0 + P[:, 0] * height, u) + np.outer(P[:, 1] * height, v)
            canvas.poly(Q, False, tier, z, tags)
        for cx, cy, rr, filled in g.get("c", []):
            q = origin + (s0 + cx * height) * u + cy * height * v
            if filled:
                canvas.dot(rr * height, q[0], q[1], z=z, tags=tags)
            else:
                canvas.circle(rr * height, q[0], q[1], tier, z, tags)
    return len(items)
