"""Interior figures (skeletons) and centres.

Figures (spec "kind"):
  star      {n/k} star polygon / compound / polygon (k=1); mode line | weave | lane | lanew (lanes that interlace)
            | merge (lanes whose crossings open into one outline). Points touch the disc ring; lanes are clipped there.
  compass   4 / 8 kite spikes (cardinal long, diagonal short); long ones may pierce the frame
  lens      n vesica petals (Frieren)            spokes   radial spokes + concentric arc cells (stained glass)
  lattice   seed / flower of life, Metatron      chain    inscribed polygon ↔ circle chain (squaring the circle)
  stave     galdrastafir radial arms             sigil    kamea / wheel trace of the seed text
  seal      Goetia-style mirrored glyph          none
Each draw function returns {"vertices": [(x, y)], "inner": r} — node anchor points and the free radius left for
the centre (or for the next disc of a tower).
"""
from __future__ import annotations

import math

import numpy as np

from . import script, sigil, stave, symbols
from .canvas import line_isect, polar, seg_intersect


def star_inner(n, k):
    """Radius (fraction of the circumradius) of the inner polygon of {n/k}."""
    if k <= 1:
        return math.cos(math.pi / n)
    return math.cos(math.pi * k / n) / math.cos(math.pi * (k - 1) / n)


def star_comps(n, k, r, rot):
    V = [polar(r, rot + i * 360.0 / n) for i in range(n)]
    g = math.gcd(n, k)
    return [[V[(s0 + j * k) % n] for j in range(n // g)] for s0 in range(g)]


def _lane_quads(comp, h):
    """Offset corners of a closed path: per edge (left start, left end, right end, right start)."""
    m = len(comp)
    P = np.asarray(comp, float)
    d = np.roll(P, -1, axis=0) - P
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    nrm = np.column_stack([-d[:, 1], d[:, 0]])
    corners = []
    for j in range(m):                       # corner at vertex j between edge j-1 and edge j
        a, b = (j - 1) % m, j
        L = line_isect(P[j] + h * nrm[a], d[a], P[j] + h * nrm[b], d[b]) or tuple(P[j] + h * nrm[b])
        R = line_isect(P[j] - h * nrm[a], d[a], P[j] - h * nrm[b], d[b]) or tuple(P[j] - h * nrm[b])
        corners.append((L, R))
    quads = []
    for j in range(m):
        L0, R0 = corners[j]
        L1, R1 = corners[(j + 1) % m]
        quads.append((L0, L1, R1, R0))
    return quads


def draw_star(cv, f, ctx):
    n, k, r = f["n"], f["k"], f["r"]
    rot = ctx["phase"] + f.get("rot", 0.0)
    mode = f.get("mode", "line")
    tier = f.get("tier", "medium")
    z = ctx["zf"]
    uid = ctx["uid"]()
    comps = star_comps(n, k, r, rot)
    if k == 1 and mode in ("weave", "lanew", "merge"):
        mode = "line" if mode == "weave" else "lane"
    if mode == "line":
        for comp in comps:
            cv.poly(comp, True, tier, z, ctx["tags"])
    else:
        edges = []
        for ci, comp in enumerate(comps):
            for j in range(len(comp)):
                edges.append((comp[j], comp[(j + 1) % len(comp)], ci, j))
        etag = [f"{uid}e{i}" for i in range(len(edges))]
        # crossings between edge centre lines
        cross = []
        for i in range(len(edges)):
            for j in range(i + 1, len(edges)):
                res = seg_intersect(edges[i][0], edges[i][1], edges[j][0], edges[j][1])
                if res:
                    cross.append((i, j, res[0], res[1]))
        over = {}
        if mode in ("weave", "lanew"):
            per_edge = {i: [] for i in range(len(edges))}
            for c, (i, j, t, u) in enumerate(cross):
                per_edge[i].append((t, c))
                per_edge[j].append((u, c))
            base = 0
            for ci, comp in enumerate(comps):
                nxt = True
                for jj in range(len(comp)):
                    e = base + jj
                    for _, c in sorted(per_edge[e]):
                        i, j = cross[c][0], cross[c][1]
                        other = j if i == e else i
                        if c in over:
                            nxt = over[c] != e
                        else:
                            over[c] = e if nxt else other
                            nxt = not nxt
                base += len(comp)
        if mode == "weave":
            gap = f.get("gap", 0.02)
            for i, (p0, p1, _, _) in enumerate(edges):
                cv.line(p0, p1, tier, z, (*ctx["tags"], etag[i]))
            for c, (i, j, t, u) in enumerate(cross):
                o = over[c]
                un = j if o == i else i
                p0, p1 = edges[o][0], edges[o][1]
                cv.clear_caps([[p0, p1]], gap + ctx["W"][tier] / ctx["s"], z=z + 0.4, only=[etag[un]])
        else:
            h = f.get("lw", 0.03)
            quads = []
            quads_g = []
            gap = f.get("gap", 0.018)
            for comp in comps:
                quads += _lane_quads(comp, h)
                quads_g += _lane_quads(comp, h + gap)
            ltier = f.get("ltier", "thin")
            for i, q in enumerate(quads):
                L0, L1, R1, R0 = q
                tg = (*ctx["tags"], etag[i], f"{uid}lane")
                cv.line(L0, L1, ltier, z, tg)
                cv.line(R0, R1, ltier, z, tg)
                if f.get("center_line"):
                    cv.line(edges[i][0], edges[i][1], "hair", z, tg)
            if mode == "merge":
                for i, q in enumerate(quads):
                    cv.clear_poly(_shrink(q, 1e-4), z=z + 0.4, only=[etag[j] for j in range(len(quads)) if j != i])
            elif mode == "lanew":
                for c, (i, j, t, u) in enumerate(cross):
                    o = over[c]
                    un = j if o == i else i
                    cv.clear_poly(quads_g[o], z=z + 0.4, only=[etag[un]])
            clip = f.get("clip", r)
            if clip:
                cv.clip_outside(clip, z=z + 0.4, only=[f"{uid}lane"])
    V = [polar(r, rot + i * 360.0 / n) for i in range(n)]
    ri = r * star_inner(n, k)
    if f.get("inner_poly") and k > 1:
        cv.poly([polar(ri, rot + 180.0 / n + i * 360.0 / n) for i in range(n)], True, "hair", z, ctx["tags"])
    inner = ri * (math.cos(math.pi / n) if k > 1 else 1.0)
    if mode != "line" and mode != "weave":
        inner -= f.get("lw", 0.03) * 1.2
    IV = [polar(ri, rot + 180.0 / n + i * 360.0 / n) for i in range(n)] if k > 1 else []
    return {"vertices": V, "inner_vertices": IV, "inner": inner}


def _shrink(q, e):
    P = np.asarray(q, float)
    c = P.mean(0)
    return c + (P - c) * (1 - e)


def draw_compass(cv, f, ctx):
    n, r = f["n"], f["r"]
    rot = ctx["phase"] + f.get("rot", 0.0)
    z = ctx["zf"]
    V = []
    for i in range(n):
        a = rot + i * 360.0 / n
        big = (i % 2 == 0) or n == 4
        tip = f["long"] if big else f["short"]
        w = f.get("w", 0.09) * (1 if big else 0.75)
        base = f.get("base", 0.0)
        side_r = max(base, tip * 0.22)
        pts = [polar(base, a), polar(side_r, a - math.degrees(w / max(side_r, 1e-3)) * 0.9), polar(tip, a),
               polar(side_r, a + math.degrees(w / max(side_r, 1e-3)) * 0.9)]
        cv.poly(pts, True, f.get("tier", "thin"), z, ctx["tags"])
        cv.line(polar(base, a), polar(tip, a), "hair", z, ctx["tags"])
        if tip > 1.0:                                  # piercing spike: cut the frame lines around it
            cv.clear_poly(_grow(pts, 0.02), z=ctx["zf"], only=None)      # cuts rings / band lines, not the spike
        V.append(polar(tip, a))
    return {"vertices": V, "inner_vertices": [], "inner": f.get("base", 0.0) or r * 0.2}


def _grow(pts, e):
    P = np.asarray(pts, float)
    c = P.mean(0)
    d = P - c
    L = np.linalg.norm(d, axis=1, keepdims=True)
    return c + d * (1 + e / np.maximum(L, 1e-6))


def draw_lens(cv, f, ctx):
    n, r = f["n"], f["r"]
    rot = ctx["phase"] + f.get("rot", 0.0)
    z = ctx["zf"]
    for L in range(f.get("layers", 1)):
        r0 = f.get("r0", 0.0)
        r1 = r if L == 0 else r * f.get("len2", 0.6)
        bulge = f.get("bulge", 0.28) * (r1 - r0)
        ph = rot + (180.0 / n if L == 1 else 0.0)
        for i in range(n):
            a = ph + i * 360.0 / n
            A = np.array(polar(r0, a))
            B = np.array(polar(r1, a))
            d = B - A
            nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) or 1)
            t = np.linspace(0, 1, 32)[:, None]
            base = A + d * t
            off = np.sin(np.pi * t) * bulge
            cv.poly(np.vstack([base + nrm * off, (base - nrm * off)[::-1]]), True, "thin" if L == 0 else "hair", z,
                    ctx["tags"])
            if f.get("vein"):
                cv.line(tuple(A), tuple(B), "hair", z, ctx["tags"])
    V = [polar(r, rot + i * 360.0 / n) for i in range(n)]
    return {"vertices": V, "inner_vertices": [polar(r * 0.55, rot + 180 / n + i * 360.0 / n) for i in range(n)],
            "inner": f.get("r0", 0.0) or r * 0.18}


def draw_spokes(cv, f, ctx):
    m, r0, r = f["m"], f["r0"], f["r"]
    rot = ctx["phase"] + f.get("rot", 0.0)
    z = ctx["zf"]
    for i in range(m):
        a = rot + i * 360.0 / m
        cv.line(polar(r0, a), polar(r, a), "thin" if i % max(1, m // f.get("n", m)) == 0 else "hair", z, ctx["tags"])
    levels = f.get("levels", 2)
    for L in range(1, levels + 1):
        rr = r0 + (r - r0) * L / (levels + 1)
        for i in range(m):
            if (i + L) % 2 == 0:
                a = rot + i * 360.0 / m
                cv.arc(rr, a, a + 360.0 / m, tier="hair", z=z, tags=ctx["tags"])
    cv.circle(r0, tier="thin", z=z, tags=ctx["tags"])
    return {"vertices": [polar(r, rot + i * 360.0 / m) for i in range(m)], "inner_vertices": [], "inner": r0}


def draw_lattice(cv, f, ctx):
    r = f["r"]
    kind = f.get("lat", "flower")
    rot = ctx["phase"] + f.get("rot", 0.0)
    z = ctx["zf"]
    uid = ctx["uid"]()
    tg = (*ctx["tags"], uid)
    if kind == "seed":
        rho = r / 2
        cv.circle(rho, tier="thin", z=z, tags=tg)
        for i in range(6):
            cv.circle(rho, *polar(rho, rot + i * 60), tier="thin", z=z, tags=tg)
        inner = rho * 0.5
    elif kind == "flower":
        rho = r / f.get("rings", 3)
        pts = set()
        R = f.get("rings", 3)
        for q in range(-R, R + 1):
            for s in range(-R, R + 1):
                x = rho * (q + s / 2)
                y = rho * s * math.sqrt(3) / 2
                if math.hypot(x, y) <= rho * (R - 1) + 1e-6:
                    pts.add((round(x, 9), round(y, 9)))
        for x, y in sorted(pts):
            t = math.radians(rot)
            X, Y = x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t)
            cv.circle(rho, X, Y, tier="hair", z=z, tags=tg)
        cv.clip_outside(r, z=z + 0.4, only=[uid])
        inner = rho * 0.4
    elif kind == "fruit":                                # fruit of life: 13 circles, none overlapping
        rho = r / 6.0
        C = [(0.0, 0.0)] + [polar(2 * rho, rot + i * 60) for i in range(6)] + [polar(4 * rho, rot + i * 60) for i in range(6)]
        for x, y in C:
            cv.circle(rho, x, y, tier="thin", z=z, tags=tg)
        inner = rho * 0.6
    elif kind == "vesica":                               # square grid of overlapping circles
        k = f.get("rings", 3)
        rho = r / k
        for i in range(-k, k + 1):
            for j in range(-k, k + 1):
                x, y = i * rho, j * rho
                if math.hypot(x, y) <= r:
                    t = math.radians(rot)
                    cv.circle(rho, x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t),
                              tier="hair", z=z, tags=tg)
        cv.clip_outside(r, z=z + 0.4, only=[uid])
        inner = rho * 0.4
    elif kind == "trigrid":                              # triangular line grid
        k = f.get("rings", 3) * 2
        h = r * 2 / k
        for a in (0, 60, 120):
            for i in range(-k, k + 1):
                d = i * h * math.sqrt(3) / 2
                with cv.at(0, 0, 1, rot + a):
                    cv.line((-2 * r, d), (2 * r, d), "hair", z, tg)
        cv.clip_outside(r, z=z + 0.4, only=[uid])
        inner = 0.0
    elif kind == "rose":                                 # n circles through the centre
        m = f.get("m", 6)
        rho = r / 2
        for i in range(m):
            cv.circle(rho, *polar(rho, rot + i * 360.0 / m), tier="thin", z=z, tags=tg)
        inner = 0.0
    else:                                                # Metatron's cube
        rho = r / 4.2
        C = [(0.0, 0.0)] + [polar(2 * rho, rot + i * 60) for i in range(6)] + [polar(4 * rho, rot + i * 60) for i in range(6)]
        for x, y in C:
            cv.circle(rho * 0.9, x, y, tier="hair", z=z, tags=tg)
        for i in range(len(C)):
            for j in range(i + 1, len(C)):
                cv.line(C[i], C[j], "hair", z, (*tg, uid + "L"))
        for x, y in C:
            cv.clear_disc(rho * 0.9 - 0.004, x, y, z=z + 0.4, only=[uid + "L"])
        inner = rho * 0.5
    if f.get("overlay"):                                 # a star laid over the lattice
        k = f["overlay"]
        for comp in star_comps(6, k, r, rot):
            cv.poly(comp, True, "thin", z + 0.2, ctx["tags"])
    return {"vertices": [polar(r, rot + i * 60) for i in range(6)], "inner_vertices": [], "inner": inner}


def draw_chain(cv, f, ctx):
    r = f["r"]
    rot = ctx["phase"] + f.get("rot", 0.0)
    z = ctx["zf"]
    V = None
    cur = r
    for m in f["seq"]:
        P = [polar(cur, rot + i * 360.0 / m) for i in range(m)]
        cv.poly(P, True, f.get("tier", "medium"), z, ctx["tags"])
        V = V or P
        cur *= math.cos(math.pi / m)
        cv.circle(cur, tier="thin", z=z, tags=ctx["tags"])
        rot += 180.0 / m if f.get("alt", True) else 0.0
    return {"vertices": V or [], "inner_vertices": [], "inner": cur}


def draw_stave(cv, f, ctx):
    stave.draw(cv, f["stave"], f["r"] * f.get("r0", 0.12), f["r"] * 0.96, ctx["phase"] + f.get("rot", 0.0),
               f.get("tier", "medium"), "thin", ctx["zf"], ctx["tags"])
    return {"vertices": [polar(f["r"], ctx["phase"] + i * 360 / f["stave"]["n"]) for i in range(f["stave"]["n"])],
            "inner_vertices": [], "inner": 0.0}


def draw_sigil(cv, f, ctx):
    r = f["r"]
    text = ctx.get("text", "magic")
    if f.get("method", "kamea") == "kamea":
        g = sigil.kamea(text, f.get("sq", 5), f.get("sym", 0), f.get("map", "pyth"), f.get("end", "bar"))
        side = r * 1.3
        n = f.get("sq", 5)
        back = f.get("backdrop") or ("dots" if f.get("cells") else "none")
        with cv.at(0, 0, side, 0):
            if back == "dots":                                # faint dots on every cell
                for i in range(n):
                    for j in range(n):
                        cv.dot(0.025 / n, (i + 0.5) / n - 0.5, (j + 0.5) / n - 0.5, z=ctx["zf"], tags=ctx["tags"], glow=0.5)
            elif back == "marks":                               # tiny crosses where grid lines would meet
                e = 0.06 / n
                for i in range(1, n):
                    for j in range(1, n):
                        x, y = i / n - 0.5, j / n - 0.5
                        cv.line((x - e, y), (x + e, y), "hair", ctx["zf"], ctx["tags"], glow=0.4)
                        cv.line((x, y - e), (x, y + e), "hair", ctx["zf"], ctx["tags"], glow=0.4)
            for s in g["s"]:
                cv.poly(np.asarray(s) - 0.5, False, f.get("tier", "thin"), ctx["zf"] + 0.5, ctx["tags"])
            for x, y, rr, fl in g["c"]:
                if fl:
                    cv.dot(rr, x - 0.5, y - 0.5, z=ctx["zf"] + 0.5, tags=ctx["tags"])
                else:
                    cv.circle(rr, x - 0.5, y - 0.5, tier=f.get("tier", "thin"), z=ctx["zf"] + 0.5, tags=ctx["tags"])
            for x, y in g["s"][0][1:-1]:                       # every traced letter cell lights up
                cv.dot(0.07 / n, x - 0.5, y - 0.5, z=ctx["zf"] + 0.5, tags=ctx["tags"])
    else:
        g = sigil.wheel(text, tuple(f.get("rings", (6, 8, 12))), ctx["phase"], f.get("end", "bar"))
        side = r * 2.0
        with cv.at(0, 0, side, 0):
            for _, x, y, rr in g["rings"]:
                cv.circle(rr, x - 0.5, y - 0.5, tier="hair", z=ctx["zf"], tags=ctx["tags"], glow=0.4)
            for x, y in g["slots"]:
                cv.dot(0.008, x - 0.5, y - 0.5, z=ctx["zf"], tags=ctx["tags"], glow=0.6)
            for x, y in g["s"][0][1:-1]:
                cv.dot(0.014, x - 0.5, y - 0.5, z=ctx["zf"] + 0.5, tags=ctx["tags"])
            for s in g["s"]:
                cv.poly(np.asarray(s) - 0.5, False, f.get("tier", "thin"), ctx["zf"] + 0.5, ctx["tags"])
            for x, y, rr, fl in g["c"]:
                cv.circle(rr, x - 0.5, y - 0.5, tier=f.get("tier", "thin"), z=ctx["zf"] + 0.5, tags=ctx["tags"])
    return {"vertices": [], "inner_vertices": [], "inner": 0.0}


def draw_seal(cv, f, ctx):
    import random
    g = symbols.seal(random.Random(f["gseed"]), mirror=True)
    script.draw_glyph(cv, g, 0, 0, f["r"] * 1.45, 0.0, f.get("tier", "thin"), ctx["zf"], ctx["tags"])
    return {"vertices": [], "inner_vertices": [], "inner": 0.0}


def draw_grid(cv, f, ctx):
    """Dōman-like square grid inside the disc (k lines each way), optionally with a diagonal cross."""
    r, k = f["r"], f.get("k", 4)
    rot = ctx["phase"] + f.get("rot", 0.0)
    z = ctx["zf"]
    uid = ctx["uid"]()
    half = r * f.get("size", 0.72)
    with cv.at(0, 0, 1, rot):
        for i in range(k):
            t = -half + 2 * half * i / (k - 1)
            cv.line((t, -half), (t, half), "thin" if i in (0, k - 1) else "hair", z, (*ctx["tags"], uid))
            cv.line((-half, t), (half, t), "thin" if i in (0, k - 1) else "hair", z, (*ctx["tags"], uid))
        if f.get("diag"):
            cv.line((-half, -half), (half, half), "hair", z, ctx["tags"])
            cv.line((-half, half), (half, -half), "hair", z, ctx["tags"])
    V = [polar(half * math.sqrt(2), rot + 45 + 90 * i) for i in range(4)]
    return {"vertices": V, "inner_vertices": [], "inner": 0.0}


def draw_triangles(cv, f, ctx):
    """Interleaved up / down triangles of decreasing size (abstract triangle stack)."""
    r = f["r"]
    rot = ctx["phase"] + f.get("rot", 0.0)
    z = ctx["zf"]
    levels = f.get("levels", 3)
    cur = r
    V = []
    for L in range(levels):
        a0 = rot + (0 if L % 2 == 0 else 180)
        P = [polar(cur, a0 + i * 120) for i in range(3)]
        cv.poly(P, True, "medium" if L == 0 else "thin", z, ctx["tags"])
        V = V or P
        if f.get("pair"):
            cv.poly([polar(cur, a0 + 180 + i * 120) for i in range(3)], True, "thin", z, ctx["tags"])
        cur *= f.get("shrink", 0.5) if not f.get("pair") else 0.5
    return {"vertices": V, "inner_vertices": [], "inner": cur}


def draw_twist(cv, f, ctx):
    """k copies of an n-gon, each rotated by 360/(n·k): a twisted polygon rosette."""
    n, k, r = f["n"], f.get("k", 3), f["r"]
    rot = ctx["phase"] + f.get("rot", 0.0)
    z = ctx["zf"]
    for j in range(k):
        a = rot + j * 360.0 / (n * k)
        cv.poly([polar(r, a + i * 360.0 / n) for i in range(n)], True, "thin", z, ctx["tags"])
    inner = r * math.cos(math.pi / n) * (0.92 if k > 1 else 1.0)
    if f.get("ring"):
        cv.circle(inner, tier="hair", z=z, tags=ctx["tags"])
    return {"vertices": [polar(r, rot + i * 360.0 / n) for i in range(n)], "inner_vertices": [], "inner": inner * 0.9}


def draw_overlay(cv, f, ctx):
    """A star plus a second figure: petals between the points, spokes, a twisted polygon or a rose of circles."""
    info = draw_star(cv, f["star"], ctx)
    sec = f["second"]
    r = f["star"]["r"]
    n = f["star"]["n"]
    if sec == "lens":
        draw_lens(cv, {"n": n, "r": info["inner"] * 0.98, "r0": 0.0, "bulge": 0.3, "layers": 1,
                       "rot": f["star"].get("rot", 0.0) + 180.0 / n}, ctx)
        info["inner"] = info["inner"] * 0.25
    elif sec == "spokes":
        rot = ctx["phase"] + f["star"].get("rot", 0.0)
        for i in range(n):
            cv.line(polar(info["inner"] * 0.3, rot + i * 360.0 / n), polar(r, rot + i * 360.0 / n), "hair",
                    ctx["zf"], ctx["tags"])
        cv.circle(info["inner"] * 0.3, tier="thin", z=ctx["zf"], tags=ctx["tags"])
        info["inner"] = info["inner"] * 0.3
    elif sec == "twist":
        draw_twist(cv, {"n": n, "k": 2, "r": info["inner"], "rot": f["star"].get("rot", 0.0) + 180.0 / n}, ctx)
        info["inner"] = info["inner"] * 0.75
    elif sec == "rose":
        draw_lattice(cv, {"r": info["inner"], "lat": "rose", "m": n, "rot": f["star"].get("rot", 0.0)}, ctx)
        info["inner"] = 0.0
    return info


def draw_none(cv, f, ctx):
    return {"vertices": [], "inner_vertices": [], "inner": f.get("r", 0.5)}


FIGS = {"grid": draw_grid, "triangles": draw_triangles, "twist": draw_twist, "overlay": draw_overlay,
        "star": draw_star, "compass": draw_compass, "lens": draw_lens, "spokes": draw_spokes,
        "lattice": draw_lattice, "chain": draw_chain, "stave": draw_stave, "sigil": draw_sigil, "seal": draw_seal,
        "none": draw_none}


def figure(cv, f, ctx):
    return FIGS[f["kind"]](cv, f, ctx)


# ---------------------------------------------------------------- centres

def _spiral(cv, r, turns, tier, z, tags):
    t = np.linspace(0, turns * 2 * np.pi, int(turns * 60))
    rr = r * t / t[-1]
    cv.poly(np.column_stack([rr * np.sin(t), rr * np.cos(t)]), False, tier, z, tags)


def centre(cv, c, ctx):
    kind = c["kind"]
    r = c["r"]
    z = ctx["zg"] + 1
    tg = ctx["tags"]
    rng = ctx["rng"]
    rot = ctx["phase"]
    if r <= 0.01 or kind == "none":
        return
    if c.get("ring"):
        cv.circle(r, tier="thin", z=z, tags=tg)
        r *= 0.82
    if kind == "dot":
        cv.dot(r * 0.25, z=z, tags=tg)
    elif kind == "bullseye":
        k = c.get("k", 2)
        for i in range(k):
            cv.circle(r * (1 - i / (k + 0.3)) * 0.9, tier="thin" if i == 0 else "hair", z=z, tags=tg)
        cv.dot(r * 0.12, z=z, tags=tg)
    elif kind == "sunburst":
        m = c.get("m", 12)
        cv.circle(r * 0.35, tier="thin", z=z, tags=tg)
        for i in range(m):
            a = rot + i * 360.0 / m
            if c.get("wavy"):
                t = np.linspace(0, 1, 20)
                amp = min(6.0, 90.0 / m)
                pts = [polar(r * (0.45 + 0.5 * u), a + amp * math.sin(u * 3 * math.pi)) for u in t]
                cv.poly(pts, False, "hair", z, tg)
            else:
                cv.line(polar(r * 0.45, a), polar(r * (0.95 if i % 2 == 0 else 0.72), a), "hair", z, tg)
        cv.dot(r * 0.1, z=z, tags=tg)
    elif kind == "symbol":
        g = c.get("glyph") or symbols.symbol(c.get("src", "alchem"), rng, ctx["scripts"][0])
        script.draw_glyph(cv, g, 0, 0, r * 1.25, 0.0, "thin", z, tg)
    elif kind == "star":
        n, k = c.get("n", 5), c.get("k", 2)
        comps = star_comps(n, k, r * 0.9, rot)
        for comp in comps:
            cv.poly(comp, True, "thin", z, tg)
        if c.get("ring2"):
            cv.circle(r * 0.9 * star_inner(n, k) * 0.8, tier="hair", z=z, tags=tg)
    elif kind == "eye":
        script.draw_glyph(cv, symbols.eye(), 0, 0, r * 1.6, 0.0, "thin", z, tg)
    elif kind == "rosette":
        m = c.get("m", 8)
        f = {"n": m, "r": r * 0.95, "r0": 0.0, "bulge": 0.3, "layers": c.get("layers", 1), "len2": 0.6}
        draw_lens(cv, f, dict(ctx, zf=z))
    elif kind == "spiral":
        _spiral(cv, r * 0.9, c.get("turns", 2.5), "thin", z, tg)
    elif kind == "maze":
        for i, q in enumerate((0.9, 0.62, 0.34)):
            s = r * q / math.sqrt(2)
            side = rng.randrange(4)
            P = [(-s, -s), (s, -s), (s, s), (-s, s)]
            path = [P[(side + j) % 4] for j in range(5)]
            # leave a gap on the closing edge
            a, b = np.array(path[-2]), np.array(path[-1])
            path[-1] = tuple(a + (b - a) * 0.7)
            with cv.at(0, 0, 1, rot + (45 if c.get("diag") else 0)):
                cv.poly(path, False, "thin" if i == 0 else "hair", z, tg)
        cv.dot(r * 0.08, z=z, tags=tg)
    elif kind == "yinyang":
        cv.circle(r * 0.9, tier="thin", z=z, tags=tg)
        rr = r * 0.9
        t = np.linspace(0, np.pi, 30)
        up = np.column_stack([rr / 2 * np.sin(t) * -1, rr / 2 + rr / 2 * np.cos(t)])
        dn = np.column_stack([rr / 2 * np.sin(t), -rr / 2 + rr / 2 * np.cos(t)])
        with cv.at(0, 0, 1, rot):
            cv.poly(np.vstack([up, dn]), False, "thin", z, tg)
            cv.circle(rr * 0.12, 0, rr / 2, tier="hair", z=z, tags=tg)
            cv.dot(rr * 0.1, 0, -rr / 2, z=z, tags=tg)
    elif kind == "sigil":
        draw_sigil(cv, dict(c, r=r * 0.95), dict(ctx, zf=z))
    elif kind == "seal":
        draw_seal(cv, dict(c, r=r), dict(ctx, zf=z))
    elif kind == "flower":
        draw_lattice(cv, {"r": r * 0.95, "lat": "seed", "rot": 0}, dict(ctx, zf=z))
    elif kind == "stave":
        stave.draw(cv, c["stave"], r * 0.15, r * 0.95, rot, "thin", "hair", z, tg)
    elif kind == "crescent":
        script.draw_glyph(cv, symbols.moon(), -r * 0.12, 0, r * 1.5, rot, "thin", z, tg)
        script.draw_glyph(cv, symbols.sparkle(4, 0.14), r * 0.35, r * 0.1, r * 0.5, 0.0, "hair", z, tg)
    elif kind == "triad":                                # three small circles in a triangle, joined
        P = [polar(r * 0.55, rot + i * 120) for i in range(3)]
        cv.poly(P, True, "hair", z, tg)
        for x, y in P:
            cv.circle(r * 0.28, x, y, tier="thin", z=z, tags=tg)
            cv.clear_disc(r * 0.3, x, y, z=z + 0.3, only=tg)
            cv.dot(r * 0.07, x, y, z=z + 0.5, tags=tg)
    elif kind == "polys":                                # concentric polygons, alternately rotated
        m = c.get("m", 4)
        cur = r * 0.95
        for i in range(c.get("levels", 3)):
            cv.poly([polar(cur, rot + (180.0 / m if i % 2 else 0) + j * 360.0 / m) for j in range(m)], True,
                    "thin" if i == 0 else "hair", z, tg)
            cur *= math.cos(math.pi / m)
        cv.dot(r * 0.08, z=z, tags=tg)
    elif kind == "trigrams":                             # the eight trigrams around a small ring
        cv.circle(r * 0.3, tier="thin", z=z, tags=tg)
        for i in range(8):
            a = rot + i * 45
            x, y = polar(r * 0.7, a)
            bits = [(i >> k) & 1 for k in range(3)]
            script.draw_glyph(cv, symbols.trigram(bits), x, y, r * 0.38, a, "hair", z, tg)
    elif kind == "compass":
        draw_compass(cv, {"n": 8, "r": r, "long": r * 0.95, "short": r * 0.6, "w": r * 0.12, "base": 0.0,
                          "tier": "thin"}, dict(ctx, zf=z))
    elif kind == "cross":                                # cross pattée
        half = math.degrees(r * 0.42 / (r * 0.9)) / 2
        for i in range(4):
            a = rot + i * 90
            cv.poly([polar(r * 0.12, a - 40), polar(r * 0.9, a - half), polar(r * 0.9, a + half),
                     polar(r * 0.12, a + 40)], False, "thin", z, tg)
        cv.circle(r * 0.14, tier="hair", z=z, tags=tg)
