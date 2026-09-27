"""Plan -> strokes. Deterministic: build-time details (text runs, symbol picks) come from plan["detail"].

z levels per disc depth d (z = 10·d + ...): rings 1, band lines 2, figure 3, glyphs 4, centre 5, node clearance 9.
A node / satellite disc at depth d+1 draws at z >= 10(d+1) and clears everything of its parents underneath it, so
lines stop short of every sub-circle; its own clearance (10(d+1)+9) cuts only its own lines and the parents'.
"""
from __future__ import annotations

import copy
import itertools
import math
import random

import numpy as np

from . import bands as B
from . import figures as F
from . import script, symbols
from .canvas import Canvas, polar


class Ctx(dict):
    pass


def _alphabets(plan):
    alphas, seps = [], []
    for g in plan["scripts"]:
        a = script.alphabet(g)
        if not a:
            a = script.alphabet({"style": "rune", "seed": 1, "w": 0.6, "rows": 4, "smin": 1, "smax": 3,
                                 "term": "none", "p_term": 0.5, "p_bar": 0.3, "reach": 1.2, "sep": "dot", "size": 20})
        alphas.append(a)
        seps.append(script.separator(g.get("sep", "dot")))
    return alphas, seps


def _circle_hits(p0, p1, r):
    """Angles (deg) where segment p0p1 crosses the circle of radius r."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    a, b, c = d @ d, 2 * p0 @ d, p0 @ p0 - r * r
    disc = b * b - 4 * a * c
    out = []
    if a < 1e-12 or disc < 0:
        return out
    for t in ((-b - math.sqrt(disc)) / (2 * a), (-b + math.sqrt(disc)) / (2 * a)):
        if 0 <= t <= 1:
            q = p0 + d * t
            out.append(math.degrees(math.atan2(q[0], q[1])) % 360)
    return out


def node_positions(core, fig):
    nd = core.get("nodes")
    if not nd:
        return []
    m = nd["m"]
    rot = fig.get("rot", 0.0)
    off = 180.0 / m if nd["place"] in ("inner", "mid") else 0.0
    return [(rot + off + i * 360.0 / m, nd["rr"]) for i in range(m)]


def draw_disc(cv, disc, depth, s, base: dict, phase=0.0):
    z = 10.0 * depth
    uidc = base["uidc"]
    tag = f"d{next(uidc)}"
    ctx = Ctx(base, s=s, zr=z + 1, zb=z + 2, zf=z + 3, zg=z + 4, zc=z + 9, phase=phase, tags=(tag,), avoid=[],
              uid=lambda: f"u{next(uidc)}")
    core = disc["core"]
    fig = core["fig"]
    n = base["n"]
    npos = node_positions(core, fig)
    rn = core["nodes"]["r"] if core.get("nodes") else 0.0
    # crossing spans (piercing star lanes / compass spikes)
    cross_edges = []
    if fig["kind"] == "star" and fig.get("pierce"):
        for comp in F.star_comps(fig["n"], fig["k"], fig["r"], phase + fig.get("rot", 0.0)):
            for j in range(len(comp)):
                cross_edges.append((comp[j], comp[(j + 1) % len(comp)], fig.get("lw", 0.03) + fig.get("gap", 0.02)))
    if fig["kind"] == "compass":
        for i in range(fig["n"]):
            a = phase + fig.get("rot", 0.0) + i * 360.0 / fig["n"]
            tip = fig["long"] if (i % 2 == 0 or fig["n"] == 4) else fig["short"]
            cross_edges.append(((0.0, 0.0), polar(tip, a), fig.get("w", 0.09)))
    # rings
    for rg in disc["rings"]:
        B.ring(cv, rg, ctx["zr"], n, phase, ctx["tags"])
    # bands
    for b in disc["bands"]:
        rm = (b["ri"] + b["ro"]) / 2
        avoid = []
        for a, rr in npos:
            if b["ri"] - rn * 1.2 < rr < b["ro"] + rn * 1.2:
                avoid.append(((a + phase) % 360, math.degrees(math.asin(min(1.0, rn * 1.25 / max(rm, 1e-3)))) + 1.5))
        for p0, p1, hw in cross_edges:
            for a in _circle_hits(p0, p1, rm):
                avoid.append((a, math.degrees(hw * 1.6 / max(rm, 1e-3)) + 2.0))
        bctx = Ctx(ctx, avoid=avoid)
        B.band(cv, b, bctx)
    # figure
    info = F.figure(cv, fig, ctx)
    # nodes
    nd = core.get("nodes")
    if nd:
        ndisc = nd["disc"]
        if not nd.get("vary"):
            ndisc = _fix_symbols(ndisc, base)
        for a, rr in npos:
            x, y = polar(rr, a + phase)
            cv.clear_disc(nd["r"] * 1.16, x, y, z=ctx["zc"])
            with cv.at(x, y, nd["r"], a + phase):
                draw_disc(cv, ndisc, depth + 1, s * nd["r"], base)
    # tower
    inner = core.get("inner")
    if inner:
        with cv.at(0.0, 0.0, inner["s"], 0.0):
            draw_disc(cv, inner["disc"], depth, s * inner["s"], base,
                      phase=phase + (180.0 / fig["n"] if fig["kind"] == "star" else 0.0))
    # centre
    c = core.get("center")
    if c and c.get("kind", "none") != "none":
        if fig.get("hole"):                              # lattice / grid lines stop at a ring around the emblem
            cv.clear_disc(fig["hole"], z=ctx["zf"] + 0.6)
            cv.circle(fig["hole"], tier="thin", z=ctx["zf"] + 0.7, tags=ctx["tags"])
        F.centre(cv, c, ctx)
    return info


def _fix_symbols(disc, base):
    """Same symbol on every node: resolve the centre glyph once."""
    d = copy.deepcopy(disc)
    c = d["core"].get("center") or {}
    if c.get("kind") == "symbol" and "glyph" not in c:
        c["glyph"] = symbols.symbol(c.get("src", "alchem"), base["rng"], base["scripts"][0])
    return d


def draw_extras(cv, plan, base):
    for e in plan["extras"]:
        t = e["type"]
        if t == "lanes":
            m, R, h, rot = e["m"], e["R"], e["h"], e["rot"]
            V = [polar(R, rot + i * 360.0 / m) for i in range(m)]
            quads = F._lane_quads(V, h)
            rv = max((x["s"] for x in plan["extras"] if x["type"] == "sat"), default=0.2)
            for i, (L0, L1, R1, R0) in enumerate(quads):
                cv.line(L0, L1, "thin", 3.0, ("lane",))
                cv.line(R0, R1, "thin", 3.0, ("lane",))
                if e.get("center_line"):
                    cv.line(V[i], V[(i + 1) % m], "hair", 3.0, ("lane",))
                if e.get("text"):
                    p0, p1 = np.asarray(V[i], float), np.asarray(V[(i + 1) % m], float)
                    d = (p1 - p0) / np.linalg.norm(p1 - p0)
                    a, b = p0 + d * rv * 1.25, p1 - d * rv * 1.25
                    alpha, sep = base["scripts"][0], base["seps"][0]
                    toks = script.text_tokens(base["rng"], alpha, sep, 200)
                    script.lay_line(cv, alpha, toks, sep, a, b, h * 1.15, "hair", 4.0, ("lane",))
        elif t == "sat":
            x, y = e["c"]
            cv.clear_disc(e["s"] * 1.09, x, y, z=9.5)
            with cv.at(x, y, e["s"], e.get("rot", 0.0)):
                draw_disc(cv, e["disc"], 1, e["s"], base)
        elif t == "link":
            cv.line(tuple(e["p0"]), tuple(e["p1"]), e.get("tier", "hair"), 1.0, ("link",))
            if e.get("r0"):
                cv.clear_disc(e["r0"] * 1.02, e["p0"][0], e["p0"][1], z=1.5, only=["link"])
        elif t == "arc":
            cv.arc(e["r"], e["a0"], e["a0"] + e["span"], tier=e["w"], z=1.0, tags=("acc",))
        elif t == "orbit":
            cv.circle(e["r"], tier="hair", z=1.0, tags=("acc",))
        elif t == "rays":                                  # short rays outside the frame
            m, r = e["m"], e["r"]
            for i in range(m):
                a = i * 360.0 / m
                L = {"short": 0.05, "long": 0.1, "alt": 0.1 if i % 2 == 0 else 0.045}[e["kind"]]
                cv.line(polar(r, a), polar(r + L, a), "hair", 1.0, ("acc",))
        elif t == "outer":                                 # a thin halo ring around the frame
            if e["kind"] == "ring":
                cv.circle(e["r"], tier="hair", z=1.0, tags=("acc",))
            elif e["kind"] == "dotted":
                for i in range(e["m"] * 2):
                    cv.dot(0.005, *polar(e["r"], i * 180.0 / e["m"]), z=1.0, tags=("acc",))
            else:
                for i in range(e["m"]):
                    a = i * 360.0 / e["m"]
                    cv.arc(e["r"], a, a + 360.0 / e["m"] * 0.5, tier="hair", z=1.0, tags=("acc",))
        elif t == "crown":                                 # arcs / points standing on the frame
            m = max(4, e["m"] // 3)
            for i in range(m):
                a = i * 360.0 / m
                if e["kind"] == "arcs":
                    t_ = np.linspace(0, 1, 16)
                    cv.poly([polar(1.02 + 0.06 * math.sin(math.pi * u), a - 90.0 / m + u * 180.0 / m) for u in t_],
                            False, "hair", 1.0, ("acc",))
                else:
                    cv.poly([polar(1.02, a - 60.0 / m), polar(1.1, a), polar(1.02, a + 60.0 / m)], False, "hair", 1.0,
                            ("acc",))
        elif t == "ecc":
            cx, cy = polar(e["off"], e["a"])
            cv.circle(e["r"], cx, cy, tier="hair", z=1.0, tags=("acc",))
        elif t == "marks":
            m, r, sz = e["m"], e["r"], e["size"]
            for i in range(m):
                a = i * 360.0 / m
                x, y = polar(r, a)
                k = e["kind"]
                if k == "spike":
                    cv.poly([polar(r - sz * 0.3, a - math.degrees(sz * 0.35 / r)), polar(r + sz * 1.3, a),
                             polar(r - sz * 0.3, a + math.degrees(sz * 0.35 / r))], True, "thin", 2.0, ("acc",))
                elif k == "triangle":
                    cv.poly([polar(r - sz * 0.2, a - math.degrees(sz * 0.5 / r)), polar(r + sz * 0.8, a),
                             polar(r - sz * 0.2, a + math.degrees(sz * 0.5 / r))], True, 0.0, 2.0, ("acc",), fill=True)
                elif k == "dot":
                    cv.dot(sz * 0.3, x, y, z=2.0, tags=("acc",))
                elif k == "sparkle":
                    script.draw_glyph(cv, symbols.sparkle(4, 0.12), x, y, sz * 1.6, a, "hair", 2.0, ("acc",))
                else:
                    g = base["scripts"][0][base["rng"].randrange(len(base["scripts"][0]))]
                    script.draw_glyph(cv, g, x, y, sz, a, "thin", 2.0, ("acc",))


def build(plan: dict):
    rng = random.Random(plan["detail"])
    cv = Canvas(dict(plan["W"]))
    alphas, seps = _alphabets(plan)
    base = {"rng": rng, "scripts": alphas, "seps": seps, "n": max(plan["n"], 1), "W": plan["W"],
            "uidc": itertools.count(), "text": plan.get("name") or plan.get("text") or str(plan["seed"])}
    root = plan["root"]
    with cv.at(root["c"][0], root["c"][1], root["s"], root.get("rot", 0.0)):
        draw_disc(cv, root["disc"], 0, root["s"], base)
    draw_extras(cv, plan, base)
    return cv.finalize()
