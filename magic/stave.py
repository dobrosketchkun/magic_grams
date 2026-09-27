"""Radial staves after Icelandic galdrastafir (research/traditions.md §6a).

A stave is n arms from a small centre; each arm is a spine with ornaments along it and a terminal at the tip.
Arm modes: "same" (all arms identical, Helm of Awe), "alt" (two arm designs alternating), "each" (every arm
different, Vegvísir). Every ornament is mirror-symmetric about its own spine, so a design can never become a
swastika / sun-wheel (bent arms under pure rotation) — see research/traditions.md §17.
Arm space: x along the arm (0 = centre radius, 1 = tip), y across it, in units of the arm length.
"""
from __future__ import annotations

import math
import random

import numpy as np

ORN = ["bar", "bar", "arcs", "fork", "comb", "dot2", "diamond", "ring", "bar2", "xcross", "tri", "hooks", "ringbar"]
TIPS = ["cap", "cap", "trident", "fork", "ring", "bar", "comb", "arrow", "diamond", "trefoil", "crescent", "square",
        "star"]


def arm(rng: random.Random) -> dict:
    k = rng.randint(1, 3)
    ts = sorted(rng.uniform(0.25, 0.8) for _ in range(k))
    orn = [(t, rng.choice(ORN), rng.uniform(0.08, 0.16)) for t in ts]
    # keep ornaments apart
    kept = []
    for o in orn:
        if all(abs(o[0] - q[0]) > 0.13 for q in kept):
            kept.append(o)
    return {"orn": kept, "tip": rng.choice(TIPS), "tip_size": rng.uniform(0.09, 0.15)}


def _arc(cx, cy, r, a0, a1, n=16):
    t = np.radians(np.linspace(a0, a1, n))
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in t]


def arm_strokes(spec) -> tuple[list, list]:
    """Strokes of one arm in arm space (x along, y across)."""
    s = [[(0.0, 0.0), (1.0, 0.0)]]
    c = []
    for t, kind, w in spec["orn"]:
        if kind == "bar":
            s.append([(t, -w), (t, w)])
        elif kind == "bar2":
            s.append([(t - 0.03, -w), (t - 0.03, w)])
            s.append([(t + 0.03, -w * 0.7), (t + 0.03, w * 0.7)])
        elif kind == "arcs":                         # ")(" pair
            s.append(_arc(t - w * 1.2, 0, w * 1.2, -50, 50))
            s.append(_arc(t + w * 1.2, 0, w * 1.2, 130, 230))
        elif kind == "fork":
            s.append([(t + w, -w), (t, 0), (t + w, w)])
        elif kind == "comb":
            s.append([(t, -w), (t, w)])
            s.append([(t, -w), (t + w * 0.7, -w)])
            s.append([(t, w), (t + w * 0.7, w)])
        elif kind == "dot2":
            c.append((t, -w * 0.7, 0.018, True))
            c.append((t, w * 0.7, 0.018, True))
        elif kind == "diamond":
            s.append([(t - w * 0.8, 0), (t, w * 0.6), (t + w * 0.8, 0), (t, -w * 0.6), (t - w * 0.8, 0)])
        elif kind == "ring":
            c.append((t, 0, w * 0.5, False))
        elif kind == "xcross":
            s.append([(t - w * 0.6, -w), (t + w * 0.6, w)])
            s.append([(t - w * 0.6, w), (t + w * 0.6, -w)])
        elif kind == "tri":                          # triangle pointing outward, centred on the spine
            s.append([(t - w * 0.6, -w * 0.8), (t + w * 0.8, 0), (t - w * 0.6, w * 0.8), (t - w * 0.6, -w * 0.8)])
        elif kind == "hooks":                        # a hook on each side, mirror images of each other
            s.append([(t, 0), (t, w)] + _arc(t + w * 0.35, w, w * 0.35, 180, 360, 10))
            s.append([(t, 0), (t, -w)] + _arc(t + w * 0.35, -w, w * 0.35, 180, 0, 10))
        elif kind == "ringbar":
            s.append([(t, -w), (t, w)])
            c.append((t, -w - w * 0.3, w * 0.3, False))
            c.append((t, w + w * 0.3, w * 0.3, False))
    tw = spec["tip_size"]
    tip = spec["tip"]
    if tip == "cap":                                 # cup opening outward, the spine runs through its centre
        s.append(_arc(1.0, 0, tw, 100, 260))
    elif tip == "trident":
        s.append([(1.0 - tw, -tw), (1.0, -tw)])
        s.append([(1.0 - tw, tw), (1.0, tw)])
        s.append([(1.0 - tw, -tw), (1.0 - tw, tw)])
    elif tip == "fork":
        s.append([(1.0, -tw), (1.0 - tw, 0), (1.0, tw)])
    elif tip == "ring":
        c.append((1.0 + tw * 0.5, 0, tw * 0.5, False))
    elif tip == "bar":
        s.append([(1.0, -tw), (1.0, tw)])
    elif tip == "comb":
        s.append([(1.0, -tw), (1.0, tw)])
        for y in (-tw, 0, tw):
            s.append([(1.0, y), (1.0 - tw * 0.6, y)])
    elif tip == "arrow":
        s.append([(1.0 - tw, -tw * 0.8), (1.0, 0), (1.0 - tw, tw * 0.8)])
    elif tip == "trefoil":
        for dx, dy in ((tw * 0.5, 0), (0, tw * 0.5), (0, -tw * 0.5)):
            c.append((1.0 + dx, dy, tw * 0.33, False))
    elif tip == "crescent":                          # horns opening outward
        s.append(_arc(1.0 - tw * 0.2, 0, tw, -70, 70))
    elif tip == "square":
        q = tw * 0.5
        s.append([(1.0 - q, -q), (1.0 + q, -q), (1.0 + q, q), (1.0 - q, q), (1.0 - q, -q)])
    elif tip == "star":
        pts = []
        for i in range(11):
            rr = tw * 0.7 if i % 2 == 0 else tw * 0.28
            a = math.radians(i * 36)
            pts.append((1.0 + tw * 0.5 + rr * math.cos(a), rr * math.sin(a)))
        s.append(pts)
    elif tip == "diamond":
        s.append([(1.0 - tw, 0), (1.0 - tw / 2, tw * 0.5), (1.0, 0), (1.0 - tw / 2, -tw * 0.5), (1.0 - tw, 0)])
    return s, c


def sample(rng: random.Random, n: int) -> dict:
    mode = rng.choices(["same", "alt", "each"], [5, 3, 3])[0]
    if mode == "alt" and n % 2:
        mode = "same"
    if mode == "same":
        arms = [arm(rng)]
    elif mode == "alt":
        arms = [arm(rng), arm(rng)]
    else:
        arms = [arm(rng) for _ in range(n)]
    return {"n": n, "mode": mode, "arms": arms, "centre": rng.choice(["ring", "dot", "none", "ring2", "star", "square"])}


def draw(canvas, spec, r0, r1, rot=0.0, tier="medium", orn_tier="thin", z=2.0, tags=()):
    """Draw the stave: arms from radius r0 to r1."""
    n = spec["n"]
    L = r1 - r0
    for i in range(n):
        a = rot + i * 360.0 / n
        sp = spec["arms"][i % len(spec["arms"])]
        s, c = arm_strokes(sp)
        th = math.radians(a)
        ux, uy = math.sin(th), math.cos(th)            # along the arm
        vx, vy = uy, -ux                               # across
        f = lambda x, y: ((r0 + x * L) * ux + y * L * vx, (r0 + x * L) * uy + y * L * vy)
        for k, q in enumerate(s):
            canvas.poly([f(x, y) for x, y in q], False, tier if k == 0 else orn_tier, z, tags)
        for x, y, r, filled in c:
            px, py = f(x, y)
            if filled:
                canvas.dot(r * L, px, py, z=z, tags=tags)
            else:
                canvas.circle(r * L, px, py, orn_tier, z, tags)
    if spec["centre"] == "ring":
        canvas.circle(r0, tier=tier, z=z, tags=tags)
    elif spec["centre"] == "ring2":
        canvas.circle(r0, tier=tier, z=z, tags=tags)
        canvas.circle(r0 * 0.55, tier=orn_tier, z=z, tags=tags)
    elif spec["centre"] == "dot":
        canvas.dot(r0 * 0.5, z=z, tags=tags)
    elif spec["centre"] == "star":
        pts = [(r0 * (1.0 if i % 2 == 0 else 0.45) * math.sin(math.radians(rot + i * 180 / n)),
                r0 * (1.0 if i % 2 == 0 else 0.45) * math.cos(math.radians(rot + i * 180 / n))) for i in range(2 * n)]
        canvas.poly(pts, True, orn_tier, z, tags)
    elif spec["centre"] == "square":
        q = r0 * 0.75
        canvas.poly([(-q, -q), (q, -q), (q, q), (-q, q)], True, tier, z, tags)
