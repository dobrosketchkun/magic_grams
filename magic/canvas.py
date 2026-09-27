"""Stroke canvas: line-art primitives, similarity transforms, and clearance cuts (numpy only, no GEOS).

Model space: y up, the main circle has radius 1. Angles are in DEGREES, clockwise from the top (12 o'clock), so
`polar(r, 0)` is straight up and the first vertex of every figure points up.

Everything is a Stroke: a polyline (closed or open) with an absolute width, a z level and tags. Fills (dots,
filled triangles, inverted bands) are closed strokes with `fill=True`; `erase=True` strokes knock ink out.
Occluders are clearance regions (disc, polygon, capsules, outside-of-disc) registered while drawing; `finalize()`
cuts every stroke that lies below an occluder (stroke.z < occluder.z, optionally only strokes with given tags), so
lines stop short of node circles, lanes interlace, lattices clip to their disc. Cuts are found on a densified
polyline and refined by bisection, so they are exact to ~1e-6 regardless of the occluder's shape.
"""
from __future__ import annotations

import math
from contextlib import contextmanager

import numpy as np

STEP = 0.004          # densify step for cut detection (model units; circle radius 1)
MIN_PIECE = 0.004     # drop cut pieces shorter than this


def polar(r, a):
    t = math.radians(a)
    return (r * math.sin(t), r * math.cos(t))


def ang(x, y):
    """Angle (deg, clockwise from top) of a point."""
    return math.degrees(math.atan2(x, y)) % 360.0


def circle_n(r):
    return int(min(720, max(40, abs(r) * 520)))


def circle_pts(cx, cy, r, n=None):
    n = n or circle_n(r)
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([cx + r * np.sin(t), cy + r * np.cos(t)])


def arc_pts(cx, cy, r, a0, a1, n=None):
    span = a1 - a0
    n = n or max(2, int(abs(span) / 360.0 * circle_n(r)) + 2)
    t = np.radians(np.linspace(a0, a1, n))
    return np.column_stack([cx + r * np.sin(t), cy + r * np.cos(t)])


def densify(pts, closed, step=STEP):
    P = np.vstack([pts, pts[:1]]) if closed else pts
    if len(P) < 2:
        return P
    d = np.linalg.norm(np.diff(P, axis=0), axis=1)
    k = np.maximum(1, np.ceil(d / step).astype(int))
    if k.max() == 1:
        return P
    starts = np.repeat(P[:-1], k, axis=0)
    ends = np.repeat(P[1:], k, axis=0)
    frac = np.concatenate([np.arange(n) / n for n in k])[:, None]
    return np.vstack([starts + (ends - starts) * frac, P[-1:]])


def simplify_collinear(P, eps=1e-7):
    if len(P) < 3:
        return P
    a, b, c = P[:-2], P[1:-1], P[2:]
    u, v = b - a, c - b
    cross = np.abs(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0])
    dot = (u * v).sum(1)
    drop = (cross < eps) & (dot > 0)
    keep = np.concatenate([[True], ~drop, [True]])
    return P[keep]


def seg_intersect(p1, p2, p3, p4):
    """Intersection parameter (t, u) of segments p1p2 and p3p4, or None."""
    d1 = (p2[0] - p1[0], p2[1] - p1[1])
    d2 = (p4[0] - p3[0], p4[1] - p3[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
    u = ((p3[0] - p1[0]) * d1[1] - (p3[1] - p1[1]) * d1[0]) / den
    if 1e-9 < t < 1 - 1e-9 and 1e-9 < u < 1 - 1e-9:
        return t, u
    return None


def line_isect(p, d, q, e):
    """Intersection point of infinite lines p + t d and q + s e (None if parallel)."""
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-12:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


# ---------------------------------------------------------------- transforms (similarity + mirror)

class Xf:
    __slots__ = ("A", "t")

    def __init__(self, A=None, t=(0.0, 0.0)):
        self.A = np.eye(2) if A is None else A
        self.t = np.asarray(t, float)

    def then(self, tx=0.0, ty=0.0, s=1.0, rot=0.0, mirror=False):
        """Local transform applied inside the current one: p_world = self(local(p))."""
        r = math.radians(rot)
        c, sn = math.cos(r), math.sin(r)
        R = np.array([[c, sn], [-sn, c]])          # clockwise rotation (y up)
        L = s * R @ (np.diag([-1.0, 1.0]) if mirror else np.eye(2))
        return Xf(self.A @ L, self.A @ np.array([tx, ty]) + self.t)

    @property
    def scale(self):
        return math.sqrt(abs(np.linalg.det(self.A)))

    def __call__(self, pts):
        P = np.asarray(pts, float).reshape(-1, 2)
        return P @ self.A.T + self.t

    def point(self, x, y):
        p = self.A @ np.array([x, y]) + self.t
        return float(p[0]), float(p[1])


# ---------------------------------------------------------------- strokes and occluders

class Stroke:
    __slots__ = ("pts", "closed", "w", "z", "tags", "fill", "erase", "circ", "glow")

    def __init__(self, pts, closed=False, w=0.006, z=0.0, tags=(), fill=False, erase=False, circ=None, glow=1.0):
        self.pts = np.asarray(pts, float)
        self.closed = closed
        self.w = w
        self.z = z
        self.tags = frozenset(tags)
        self.fill = fill
        self.erase = erase
        self.circ = circ          # (cx, cy, r) when the stroke lies on a circle (compact SVG arcs)
        self.glow = glow

    def copy(self, pts, closed):
        return Stroke(pts, closed, self.w, self.z, self.tags, self.fill, self.erase, self.circ, self.glow)

    def length(self):
        P = np.vstack([self.pts, self.pts[:1]]) if self.closed else self.pts
        return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())


class Occ:
    """Clearance region. kind: disc (c, r) | poly (pts) | caps (segments (k,2,2), r) | outside (c, r)."""
    __slots__ = ("kind", "c", "r", "pts", "segs", "z", "only", "bbox")

    def __init__(self, kind, z, only=None, c=None, r=0.0, pts=None, segs=None):
        self.kind, self.z, self.c, self.r, self.pts, self.segs = kind, z, c, r, pts, segs
        self.only = frozenset(only) if only else None
        if kind == "disc":
            self.bbox = (c[0] - r, c[1] - r, c[0] + r, c[1] + r)
        elif kind == "poly":
            self.bbox = (*pts.min(0), *pts.max(0))
        elif kind == "caps":
            P = segs.reshape(-1, 2)
            self.bbox = (*(P.min(0) - r), *(P.max(0) + r))
        else:
            self.bbox = None                       # outside-of-disc: unbounded

    def inside(self, P):
        if self.kind == "disc":
            return (P[:, 0] - self.c[0]) ** 2 + (P[:, 1] - self.c[1]) ** 2 < self.r * self.r
        if self.kind == "outside":
            return (P[:, 0] - self.c[0]) ** 2 + (P[:, 1] - self.c[1]) ** 2 > self.r * self.r
        if self.kind == "poly":
            x, y = P[:, 0], P[:, 1]
            V = self.pts
            res = np.zeros(len(P), bool)
            j = len(V) - 1
            for i in range(len(V)):
                xi, yi = V[i]
                xj, yj = V[j]
                cond = (yi > y) != (yj > y)
                with np.errstate(divide="ignore", invalid="ignore"):
                    xint = (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi
                res ^= cond & (x < xint)
                j = i
            return res
        # capsules
        out = np.zeros(len(P), bool)
        r2 = self.r * self.r
        for a, b in self.segs:
            d = b - a
            L2 = float(d @ d) or 1e-18
            t = np.clip(((P - a) @ d) / L2, 0, 1)
            q = a + t[:, None] * d
            out |= ((P - q) ** 2).sum(1) < r2
        return out

    def applies(self, st):
        if st.z >= self.z:
            return False
        if self.only is not None and not (st.tags & self.only):
            return False
        return True


def _bbox(P, pad):
    return (P[:, 0].min() - pad, P[:, 1].min() - pad, P[:, 0].max() + pad, P[:, 1].max() + pad)


def _overlap(a, b):
    return b is None or not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def cut_stroke(st, occs):
    if st.fill or not occs:
        return [st]
    bb = _bbox(st.pts, st.w)
    rel = [o for o in occs if o.applies(st) and _overlap(bb, o.bbox)]
    if not rel:
        return [st]
    P = densify(st.pts, st.closed)
    ins = np.zeros(len(P), bool)
    for o in rel:
        ins |= o.inside(P)
    if not ins.any():
        return [st]
    if ins.all():
        return []

    def inside_one(p):
        q = np.asarray(p, float)[None]
        return any(o.inside(q)[0] for o in rel)

    def edge(pin, pout):
        a, b = np.asarray(pin, float), np.asarray(pout, float)
        for _ in range(16):
            m = (a + b) / 2
            if inside_one(m):
                a = m
            else:
                b = m
        return b

    if st.closed:                                   # densify() appended the first point: rotate to an inside point
        P = P[:-1]
        ins = ins[:-1]
        i0 = int(np.argmax(ins))
        P = np.vstack([P[i0:], P[:i0], P[i0:i0 + 1]])
        ins = np.concatenate([ins[i0:], ins[:i0], ins[i0:i0 + 1]])
    idx = np.flatnonzero(~ins)
    runs = np.split(idx, np.flatnonzero(np.diff(idx) != 1) + 1)
    out = []
    for run in runs:
        a, b = int(run[0]), int(run[-1])
        seg = P[a:b + 1]
        if a > 0:
            seg = np.vstack([edge(P[a - 1], P[a])[None], seg])
        if b < len(P) - 1:
            seg = np.vstack([seg, edge(P[b + 1], P[b])[None]])
        if len(seg) < 2:
            continue
        seg = simplify_collinear(seg)
        if np.linalg.norm(np.diff(seg, axis=0), axis=1).sum() < MIN_PIECE:
            continue
        out.append(st.copy(seg, False))
    return out


# ---------------------------------------------------------------- canvas

class Canvas:
    def __init__(self, W: dict | None = None):
        self.strokes: list[Stroke] = []
        self.occ: list[Occ] = []
        self.xf = Xf()
        self.W = W or {"heavy": 0.018, "medium": 0.01, "thin": 0.0055, "hair": 0.0035}
        self.meta: dict = {}

    # -- transform stack
    @contextmanager
    def at(self, tx=0.0, ty=0.0, s=1.0, rot=0.0, mirror=False):
        old = self.xf
        self.xf = old.then(tx, ty, s, rot, mirror)
        try:
            yield self
        finally:
            self.xf = old

    def w(self, tier):
        return self.W[tier] if isinstance(tier, str) else float(tier)

    def _add(self, pts, closed, tier, z, tags, fill=False, erase=False, circ=None, glow=1.0):
        P = self.xf(pts)
        if len(P) < 2:
            return None
        st = Stroke(P, closed, self.w(tier), z, tags, fill, erase, circ, glow)
        self.strokes.append(st)
        return st

    # -- primitives (local coordinates)
    def circle(self, r, cx=0.0, cy=0.0, tier="thin", z=0.0, tags=(), fill=False, erase=False, glow=1.0):
        if r <= 0:
            return None
        c = self.xf.point(cx, cy)
        return self._add(circle_pts(cx, cy, r, circle_n(r * self.xf.scale)), True, tier, z, tags, fill, erase,
                         circ=(c[0], c[1], r * self.xf.scale), glow=glow)

    def arc(self, r, a0, a1, cx=0.0, cy=0.0, tier="thin", z=0.0, tags=(), glow=1.0):
        if a1 - a0 >= 359.999:
            return self.circle(r, cx, cy, tier, z, tags, glow=glow)
        c = self.xf.point(cx, cy)
        n = max(2, int(abs(a1 - a0) / 360.0 * circle_n(r * self.xf.scale)) + 2)
        return self._add(arc_pts(cx, cy, r, a0, a1, n), False, tier, z, tags, circ=(c[0], c[1], r * self.xf.scale),
                         glow=glow)

    def poly(self, pts, closed=False, tier="thin", z=0.0, tags=(), fill=False, erase=False, glow=1.0):
        return self._add(np.asarray(pts, float), closed, tier, z, tags, fill, erase, glow=glow)

    def line(self, p0, p1, tier="thin", z=0.0, tags=(), glow=1.0):
        return self._add(np.array([p0, p1], float), False, tier, z, tags, glow=glow)

    def dot(self, r, cx=0.0, cy=0.0, z=0.0, tags=(), glow=1.0):
        return self.circle(r, cx, cy, tier=0.0, z=z, tags=tags, fill=True, glow=glow)

    # -- occluders (local coordinates)
    def clear_disc(self, r, cx=0.0, cy=0.0, z=5.0, only=None):
        c = self.xf.point(cx, cy)
        self.occ.append(Occ("disc", z, only, c=c, r=r * self.xf.scale))

    def clip_outside(self, r, cx=0.0, cy=0.0, z=5.0, only=None):
        c = self.xf.point(cx, cy)
        self.occ.append(Occ("outside", z, only, c=c, r=r * self.xf.scale))

    def clear_poly(self, pts, z=5.0, only=None):
        P = self.xf(pts)
        if len(P) >= 3:
            self.occ.append(Occ("poly", z, only, pts=P))

    def clear_caps(self, segs, r, z=5.0, only=None):
        S = np.asarray(segs, float).reshape(-1, 2, 2)
        if len(S):
            S = self.xf(S.reshape(-1, 2)).reshape(-1, 2, 2)
            self.occ.append(Occ("caps", z, only, segs=S, r=r * self.xf.scale))

    # -- output
    def finalize(self) -> list[Stroke]:
        out = []
        for st in self.strokes:
            out.extend(cut_stroke(st, self.occ))
        return out
