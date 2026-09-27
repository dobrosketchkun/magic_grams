"""Sigils from text (research/traditions.md §2): kamea tracing and the rose-cross letter wheel.

kamea: letters -> numbers (Pythagorean A1..I9 / A1..Z26), reduced into 1..n², traced through the cell centres of
one of Agrippa's seven planetary squares (optionally rotated / mirrored: the 8 symmetries of a magic square are
magic too). Start = small circle, end = perpendicular bar, a repeated letter = a small loop.
wheel: letters placed on 3 concentric rings of petals (Latin 6/8/12 split), traced the same way.
Output: glyph format ({"s", "c", "w"}, unit box) plus the grid / wheel geometry for an optional faint backdrop.
"""
from __future__ import annotations

import math

import numpy as np

KAMEA = {
    3: [[4, 9, 2], [3, 5, 7], [8, 1, 6]],
    4: [[4, 14, 15, 1], [9, 7, 6, 12], [5, 11, 10, 8], [16, 2, 3, 13]],
    5: [[11, 24, 7, 20, 3], [4, 12, 25, 8, 16], [17, 5, 13, 21, 9], [10, 18, 1, 14, 22], [23, 6, 19, 2, 15]],
    6: [[6, 32, 3, 34, 35, 1], [7, 11, 27, 28, 8, 30], [19, 14, 16, 15, 23, 24], [18, 20, 22, 21, 17, 13],
        [25, 29, 10, 9, 26, 12], [36, 5, 33, 4, 2, 31]],
    7: [[22, 47, 16, 41, 10, 35, 4], [5, 23, 48, 17, 42, 11, 29], [30, 6, 24, 49, 18, 36, 12],
        [13, 31, 7, 25, 43, 19, 37], [38, 14, 32, 1, 26, 44, 20], [21, 39, 8, 33, 2, 27, 45],
        [46, 15, 40, 9, 34, 3, 28]],
    8: [[8, 58, 59, 5, 4, 62, 63, 1], [49, 15, 14, 52, 53, 11, 10, 56], [41, 23, 22, 44, 45, 19, 18, 48],
        [32, 34, 35, 29, 28, 38, 39, 25], [40, 26, 27, 37, 36, 30, 31, 33], [17, 47, 46, 20, 21, 43, 42, 24],
        [9, 55, 54, 12, 13, 51, 50, 16], [64, 2, 3, 61, 60, 6, 7, 57]],
    9: [[37, 78, 29, 70, 21, 62, 13, 54, 5], [6, 38, 79, 30, 71, 22, 63, 14, 46], [47, 7, 39, 80, 31, 72, 23, 55, 15],
        [16, 48, 8, 40, 81, 32, 64, 24, 56], [57, 17, 49, 9, 41, 73, 33, 65, 25], [26, 58, 18, 50, 1, 42, 74, 34, 66],
        [67, 27, 59, 10, 51, 2, 43, 75, 35], [36, 68, 19, 60, 11, 52, 3, 44, 76], [77, 28, 69, 20, 61, 12, 53, 4, 45]],
}


def letters(text: str) -> list[str]:
    import unicodedata
    t = unicodedata.normalize("NFKD", str(text)).upper()
    out = [ch for ch in t if "A" <= ch <= "Z"]
    if not out:                                   # non-Latin seed: letters from the code points
        out = [chr(65 + (ord(ch) % 26)) for ch in str(text) if not ch.isspace()] or ["A"]
    return out[:24]


def _cells(n, sym):
    K = np.array(KAMEA[n])
    if sym & 4:
        K = K.T
    K = np.rot90(K, sym & 3)
    pos = {}
    for r in range(n):
        for c in range(n):
            pos[int(K[r, c])] = (c, n - 1 - r)
    return pos


def _loop(p, d, size):
    nx, ny = -d[1], d[0]
    cx, cy = p[0] + nx * size, p[1] + ny * size
    t = np.linspace(0, 2 * np.pi, 18)
    a0 = math.atan2(p[0] - cx, p[1] - cy)
    return [(cx + size * math.sin(a0 + a), cy + size * math.cos(a0 + a)) for a in t]


def _finish(path, size, repeats, start_kind="circle", end_kind="bar"):
    s, c = [], []
    P = [path[0]]
    for q in path[1:]:
        if math.dist(q, P[-1]) > 1e-9:
            P.append(q)
    if len(P) < 2:
        P = [(P[0][0] - 0.2, P[0][1]), (P[0][0] + 0.2, P[0][1])]
    s.append(P)
    d0 = np.subtract(P[1], P[0])
    d0 = d0 / (np.linalg.norm(d0) or 1)
    if start_kind == "circle":
        c.append((P[0][0] - d0[0] * size, P[0][1] - d0[1] * size, size, False))
    else:
        c.append((P[0][0], P[0][1], size * 0.6, True))
    d1 = np.subtract(P[-1], P[-2])
    d1 = d1 / (np.linalg.norm(d1) or 1)
    nx, ny = -d1[1], d1[0]
    x, y = P[-1]
    if end_kind == "bar":
        s.append([(x - nx * size * 1.6, y - ny * size * 1.6), (x + nx * size * 1.6, y + ny * size * 1.6)])
    elif end_kind == "arrow":
        s.append([(x - d1[0] * size * 1.5 + nx * size * 1.2, y - d1[1] * size * 1.5 + ny * size * 1.2), (x, y),
                  (x - d1[0] * size * 1.5 - nx * size * 1.2, y - d1[1] * size * 1.5 - ny * size * 1.2)])
    else:
        c.append((x + d1[0] * size, y + d1[1] * size, size, False))
    for p, d in repeats:
        s.append(_loop(p, d, size * 0.8))
    return s, c


def kamea(text: str, n: int = 5, sym: int = 0, mapping: str = "pyth", end="bar") -> dict:
    """Sigil of `text` on the n×n planetary square (n = 3..9). Returns glyph + grid lines (unit box)."""
    pos = _cells(n, sym)
    vals = []
    for ch in letters(text):
        v = (ord(ch) - 65) % 9 + 1 if mapping == "pyth" else ord(ch) - 64
        v = (v - 1) % (n * n) + 1
        vals.append(v)
    pts = [((pos[v][0] + 0.5) / n, (pos[v][1] + 0.5) / n) for v in vals]
    path, repeats = [pts[0]], []
    for q in pts[1:]:
        if math.dist(q, path[-1]) < 1e-9:
            d = np.subtract(path[-1], path[-2]) if len(path) > 1 else np.array([1.0, 0.0])
            d = d / (np.linalg.norm(d) or 1)
            repeats.append((q, tuple(d)))
        else:
            path.append(q)
    s, c = _finish(path, 0.22 / n, repeats, end_kind=end)
    grid = [[(i / n, 0), (i / n, 1)] for i in range(n + 1)] + [[(0, i / n), (1, i / n)] for i in range(n + 1)]
    return {"s": s, "c": c, "w": 1.0, "grid": grid}


def wheel(text: str, rings=(6, 8, 12), rot=0.0, end="bar") -> dict:
    """Rose-cross style wheel: A..Z spread over concentric rings of petals; letters traced in order."""
    slots = []
    total = sum(rings)
    radii = [0.18 + 0.3 * i / max(len(rings) - 1, 1) for i in range(len(rings))]
    for k, (m, r) in enumerate(zip(rings, radii)):
        for j in range(m):
            a = math.radians(rot + (j + 0.5 * (k % 2)) * 360 / m)
            slots.append((0.5 + r * math.sin(a), 0.5 + r * math.cos(a)))
    pts = [slots[(ord(ch) - 65) * total // 26 % total] for ch in letters(text)]
    path, repeats = [pts[0]], []
    for q in pts[1:]:
        if math.dist(q, path[-1]) < 1e-9:
            repeats.append((q, (1.0, 0.0)))
        else:
            path.append(q)
    s, c = _finish(path, 0.03, repeats, end_kind=end)
    guides = [("circle", 0.5, 0.5, r + 0.15 / len(rings)) for r in radii]
    return {"s": s, "c": c, "w": 1.0, "rings": guides, "slots": slots}
