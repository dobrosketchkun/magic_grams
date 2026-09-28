"""Sampler: preset x shared layers -> plan (a JSON-serialisable spec that build.py draws deterministically).

Layers shared by every preset (research/DESIGN.md §3): topology, symmetry order n, frame, band stack (outside ->
in, uneven widths, one breathing band), figure (skeleton), nodes, centre, modifiers, weights, colour, scripts.
A PRESET restricts which values each layer may take and how often, so a type keeps its character while the
combinations multiply across layers (the halo_forge pattern). Frequencies come from the coded references
(research/visual_refs.md §3-§4: 91% circle frames, 73% text bands, n 5/6 > 4/8 > 3/12 > 7/9, nodes 55%...).

Order locking: every band count, node count and figure order is a multiple (or divisor) of n, except at most one
deliberately "odd" layer (research/prior_art.md §7.4).
Sizes: all radii are local to their disc (disc radius 1); `s` is the disc's absolute scale, used to keep absolute
minimums (ring spacing, text height) so small nested circles stay legible.
"""
from __future__ import annotations

import math
import random

from . import stave as stave_mod
from .library import text_sets

# Bump whenever sampling changes: the same seed then yields a different circle (issued ones stay frozen).
GENERATOR_VERSION = "2026.09.28-6"

PALETTE = {"#6fd8ff": 9, "#5aa8ff": 6, "#ffd36a": 6, "#ff78c4": 4, "#ff6262": 3, "#b894ff": 5, "#72ffc8": 2,
           "#ffa04a": 2, "#9ff0ff": 2}
WEIGHTS = {
    "tiered": {"heavy": 0.017, "medium": 0.0095, "thin": 0.0055, "hair": 0.0034},
    "even": {"heavy": 0.0078, "medium": 0.0064, "thin": 0.0052, "hair": 0.0038},
    "bold": {"heavy": 0.026, "medium": 0.013, "thin": 0.0066, "hair": 0.0040},
    "fine": {"heavy": 0.012, "medium": 0.0072, "thin": 0.0043, "hair": 0.0029},
}
# what sits behind a kamea sigil trace (never a full grid: it reads as graph paper inside a round circle)
SIGIL_BACKDROP = {"none": 4, "dots": 3, "marks": 2}
MIN_SEP = 0.012       # absolute minimum distance between concentric ring lines
MIN_TEXT = 0.032       # absolute minimum text band width

# band kind -> (min width, max width) local at the root, edge rings (p outer line, p inner line)
BAND = {
    "text": ((0.07, 0.115), (0.9, 0.9)), "inverted": ((0.065, 0.09), (0.6, 0.6)),
    "glyphs": ((0.1, 0.15), (0.6, 0.6)), "roundels": ((0.1, 0.15), (0.75, 0.75)),
    "ticks": ((0.03, 0.06), (0.8, 0.3)), "dots": ((0.02, 0.035), (0.3, 0.3)), "beads": ((0.03, 0.045), (0.3, 0.3)),
    "loops": ((0.05, 0.08), (0.4, 0.4)), "zigzag": ((0.04, 0.07), (0.9, 0.9)), "chevrons": ((0.04, 0.06), (0.6, 0.6)),
    "wave": ((0.035, 0.06), (0.5, 0.5)), "braid": ((0.05, 0.075), (0.6, 0.6)), "crenel": ((0.03, 0.05), (0.4, 0.4)),
    "meander": ((0.05, 0.075), (0.8, 0.8)), "scallop": ((0.03, 0.05), (0.2, 0.9)), "cells": ((0.08, 0.12), (1.0, 1.0)),
    "orbit": ((0.04, 0.07), (0.0, 0.0)), "arcs": ((0.014, 0.026), (0.2, 0.2)), "gear": ((0.03, 0.05), (0.0, 0.6)),
    "petals": ((0.06, 0.11), (0.2, 0.8)), "sparkles": ((0.05, 0.08), (0.3, 0.3)), "empty": ((0.04, 0.11), (0.0, 0.0)),
    "diamonds": ((0.04, 0.07), (0.5, 0.5)), "crosses": ((0.04, 0.07), (0.4, 0.4)), "ladder": ((0.03, 0.05), (0.0, 0.0)),
    "triangles": ((0.035, 0.06), (0.6, 0.6)), "stars": ((0.05, 0.08), (0.3, 0.3)), "hatch": ((0.03, 0.05), (0.9, 0.9)),
    "vesica": ((0.04, 0.07), (0.4, 0.4)), "keys": ((0.04, 0.06), (0.8, 0.8)),
}

# ---------------------------------------------------------------- presets

T = "text"
PRESETS = {
    "minimal": dict(freq=6, n=[5, 6, 5, 6, 4, 8, 3, 7], style={"tiered": 3, "even": 1, "fine": 1},
                    frame=["line", "double", "heavy2"], bands=(0, 2),
                    pool={T: 4, "ticks": 1, "dots": 1, "empty": 1, "beads": 1}, text=0.55,
                    fig={"star": 6, "none": 1}, star_modes={"line": 4, "weave": 2, "lanew": 1},
                    nodes=0.35, center={"none": 2, "dot": 2, "bullseye": 2, "symbol": 2, "star": 1}),
    "solomonic": dict(freq=9, n=[5, 6, 7, 8, 5, 6, 4], style={"tiered": 4, "fine": 1},
                      frame=["double", "heavy2", "double"], bands=(1, 3),
                      pool={T: 6, "glyphs": 1, "cells": 1, "dots": 1, "empty": 1}, text=1.0, text2=0.45,
                      fig={"star": 5, "none": 1, "chain": 1}, star_modes={"line": 3, "weave": 2, "lanew": 1},
                      nodes=0.25, center={"symbol": 3, "sigil": 2, "seal": 1, "star": 1, "eye": 1}, segments=0.5),
    "midchilda": dict(freq=7, n=[4, 8, 4], style={"even": 2, "tiered": 1}, frame=["line", "double"],
                      bands=(1, 3), pool={T: 5, "glyphs": 2, "dots": 1, "ticks": 1}, text=1.0, text2=0.5,
                      fig={"star": 1}, star_k={4: [1], 8: [2]}, star_modes={"lane": 2, "merge": 2, "lanew": 1},
                      nodes=0.8, node_place=["vertex"], node=["ringed", "symbol", "star"],
                      center={"bullseye": 2, "star": 2, "symbol": 1, "maze": 1}, pierce=0.45),
    "belka": dict(freq=3, n=[3], style={"even": 2, "tiered": 1}, frame=["line", "double"], bands=(0, 2),
                  pool={T: 4, "dots": 1, "ticks": 1}, text=0.7, fig={"star": 1}, star_k={3: [1], 6: [2]},
                  star_modes={"line": 2, "lane": 1, "weave": 1}, nodes=0.3, topo="belka",
                  center={"star": 2, "bullseye": 1, "symbol": 1}),
    "squared": dict(freq=3, n=[4], style={"even": 1, "tiered": 1}, frame=["line", "double"], bands=(0, 2),
                    pool={T: 4, "dots": 1, "glyphs": 1}, text=0.7, fig={"star": 1}, star_k={4: [1], 8: [2, 3]},
                    star_modes={"line": 2, "lane": 1, "weave": 1}, nodes=0.3, topo="square",
                    center={"star": 2, "bullseye": 1, "symbol": 1, "maze": 1}),
    "goetic": dict(freq=3, n=[1], style={"fine": 2, "tiered": 1}, frame=["double", "double", "heavy2"],
                   bands=(1, 1), pool={T: 1}, text=1.0, fig={"seal": 1}, nodes=0.0, center={"none": 1},
                   big_text=True, min_ideas=2),
    "tower": dict(freq=6, n=[7, 5, 6, 8, 9, 7], style={"tiered": 3, "fine": 2}, frame=["double", "heavy2", "line"],
                  bands=(1, 2), pool={"cells": 3, T: 3, "glyphs": 1}, text=0.7, fig={"star": 1}, tower=(2, 3),
                  star_modes={"line": 4, "weave": 1}, nodes=0.2, center={"symbol": 2, "star": 1, "dot": 1, "sigil": 1}),
    "clockwork": dict(freq=7, n=[12, 6, 4, 3, 12], style={"tiered": 2, "fine": 2}, frame=["heavy2", "double", "line"],
                      bands=(3, 5), pool={"ticks": 5, "glyphs": 3, "cells": 2, "gear": 2, "orbit": 2, "dots": 1, T: 2,
                                          "empty": 1, "arcs": 1},
                      text=0.4, fig={"spokes": 2, "none": 2, "star": 2}, star_modes={"line": 3, "weave": 1},
                      nodes=0.25, glyph_src=["numeral", "zodiac", "script", "lib:hershey_astro"],
                      center={"sunburst": 3, "bullseye": 2, "star": 1, "symbol": 1}, eccentric=0.5),
    "lens": dict(freq=5, n=[4, 6, 8, 4], style={"even": 1}, frame=["line", "double"], bands=(1, 3),
                 pool={T: 5, "roundels": 2, "dots": 1, "beads": 1}, text=1.0, scripts=["block", "rune", "angular"],
                 fig={"lens": 1}, nodes=0.45, node=["spiral", "bullseye", "symbol", "ringed", "star"],
                 center={"maze": 2, "spiral": 2, "bullseye": 1, "rosette": 1}),
    "tiles": dict(freq=4, n=[8, 4, 6], style={"tiered": 1, "bold": 1}, frame=["line", "double"], bands=(2, 3),
                  pool={"glyphs": 4, T: 4, "cells": 2}, text=1.0, segments=0.7, glyph_frame=["square"],
                  fig={"star": 1}, star_k={8: [3], 4: [1], 6: [2]}, star_modes={"line": 3, "weave": 1},
                  nodes=0.2, center={"symbol": 2, "star": 1, "eye": 1}),
    "ink": dict(freq=5, n=[1], style={"bold": 3, "tiered": 1}, frame=["heavy2", "line", "double"], bands=(2, 4),
                pool={"zigzag": 3, "chevrons": 3, T: 2, "loops": 2, "scallop": 2, "braid": 1, "sparkles": 1},
                text=0.5, fig={"seal": 3, "sigil": 2, "star": 1}, star_k={3: [1]}, fig_n=3,
                star_modes={"line": 1}, nodes=0.0, center={"none": 1}, marks=0.5),
    "celestial": dict(freq=5, n=[12, 12, 6], style={"tiered": 2, "fine": 1}, frame=["double", "heavy2"], bands=(2, 3),
                      pool={"ticks": 3, "glyphs": 3, T: 2, "dots": 1, "cells": 1}, text=0.6,
                      glyph_src=["zodiac", "lib:hershey_astro", "zodiac"], fig={"star": 1},
                      star_k={12: [4, 5, 3], 6: [2]}, star_modes={"line": 3, "weave": 1}, nodes=0.2,
                      center={"sunburst": 2, "symbol": 1, "eye": 1}, offcentre=0.7),
    "scholarly": dict(freq=4, n=[4, 6, 5, 8], style={"fine": 2, "tiered": 1}, frame=["line", "double"], bands=(2, 4),
                      pool={T: 5, "dots": 1, "ticks": 1, "beads": 1, "arcs": 1}, text=1.0, text2=0.7,
                      fig={"star": 2, "none": 1, "spokes": 1}, star_modes={"line": 2, "weave": 1}, nodes=0.2,
                      center={"symbol": 2, "sigil": 1, "bullseye": 1}, topo="graph"),
    "stave": dict(freq=3, n=[8, 8, 6, 4], style={"tiered": 2, "bold": 1}, frame=["line", "double", "heavy2"],
                  bands=(1, 2), pool={T: 4, "dots": 1, "ticks": 1}, text=0.8, scripts=["rune", "lib:runic",
                                                                                        "lib:old_turkic"],
                  fig={"stave": 1}, nodes=0.0, center={"none": 1}, min_ideas=2),
    "rosette": dict(freq=4, n=[6, 8, 10, 12, 8], style={"tiered": 2, "fine": 1}, frame=["double", "line"],
                    bands=(1, 3), pool={"braid": 3, "meander": 2, T: 3, "petals": 2, "beads": 1}, text=0.5,
                    fig={"star": 1}, tower=(2, 2), tower_ring=0.3, star_modes={"weave": 3, "lanew": 3},
                    nodes=0.1, center={"rosette": 2, "star": 1, "dot": 1}),
    "alchemical": dict(freq=4, n=[3, 4, 3], style={"tiered": 2, "fine": 1}, frame=["double", "line", "heavy2"],
                       bands=(1, 2), pool={T: 5, "glyphs": 1, "dots": 1}, text=0.8,
                       fig={"chain": 3, "star": 1}, nodes=0.6, node_place=["vertex"], node=["symbol", "ringed"],
                       node_src=["alchem", "lib:alchemical", "lib:hershey_astro"],
                       center={"symbol": 3, "eye": 1, "sigil": 1}),
    "trigram": dict(freq=3, n=[8, 4], style={"tiered": 1, "fine": 1}, frame=["double", "line"], bands=(2, 3),
                    pool={"glyphs": 3, T: 3, "cells": 1, "dots": 1}, text=0.6, glyph_src=["trigram", "trigram", "geomantic"],
                    must=["glyphs"], fig={"star": 2, "none": 1}, star_k={8: [3, 2], 4: [1]},
                    star_modes={"line": 2, "weave": 1}, nodes=0.1, center={"yinyang": 2, "bullseye": 1, "star": 1}),
    "compass": dict(freq=4, n=[4, 8], style={"tiered": 2, "even": 1}, frame=["line", "double", "heavy2"], bands=(1, 3),
                    pool={T: 4, "ticks": 2, "dots": 1, "glyphs": 1}, text=0.8, fig={"compass": 1}, nodes=0.2,
                    center={"bullseye": 1, "symbol": 1, "star": 1, "sunburst": 1}),
    "lattice": dict(freq=3, n=[6], style={"fine": 2, "tiered": 1}, frame=["double", "line"], bands=(1, 2),
                    pool={T: 4, "beads": 1, "dots": 1, "petals": 1}, text=0.7, fig={"lattice": 1}, nodes=0.4,
                    center={"none": 1}),
    "sigil": dict(freq=4, n=[4, 8, 6, 5], style={"tiered": 2, "fine": 1}, frame=["double", "heavy2"], bands=(2, 3),
                  pool={T: 5, "dots": 1, "ticks": 1, "glyphs": 1}, text=1.0, fig={"sigil": 1}, nodes=0.0, min_ideas=2,
                  center={"none": 1}),
    "radiant": dict(freq=4, n=[8, 12, 16, 6], style={"tiered": 2, "bold": 1}, frame=["line", "heavy2", "double"],
                    bands=(2, 4), pool={"petals": 3, "sparkles": 2, "ticks": 2, T: 3, "wave": 1, "loops": 2, "dots": 1},
                    text=0.5, fig={"star": 2, "lens": 1, "none": 1}, star_modes={"line": 2, "weave": 2},
                    nodes=0.2, center={"sunburst": 2, "rosette": 2, "star": 1}),
    # broad pools over every layer: the critic keeps it on-style, the combinations multiply
    "freeform": dict(freq=24, n=[3, 4, 5, 6, 7, 8, 9, 10, 12, 5, 6, 8], style={"tiered": 3, "fine": 2, "even": 1, "bold": 1},
                     frame=["line", "double", "heavy2", "double"], bands=(1, 4),
                     pool={T: 6, "glyphs": 2, "roundels": 2, "ticks": 2, "dots": 2, "beads": 1, "loops": 1, "zigzag": 1,
                           "chevrons": 1, "wave": 1, "braid": 1, "crenel": 1, "meander": 1, "scallop": 1, "cells": 1,
                           "orbit": 1, "arcs": 1, "gear": 1, "petals": 1, "sparkles": 1, "inverted": 1, "empty": 1,
                           "diamonds": 1, "crosses": 1, "ladder": 1, "triangles": 1, "stars": 1, "hatch": 1, "vesica": 1,
                           "keys": 1},
                     text=0.75, text2=0.3, segments=0.35,
                     fig={"star": 6, "lens": 1, "spokes": 1, "chain": 1, "compass": 1, "lattice": 1, "none": 1,
                          "triangles": 1, "twist": 2, "overlay": 3},
                     star_modes={"line": 3, "weave": 2, "lanew": 1, "lane": 1, "merge": 1}, nodes=0.45, pierce=0.08,
                     tower=(1, 2), center={"symbol": 3, "bullseye": 2, "sunburst": 1, "star": 2, "eye": 1, "rosette": 1,
                                           "spiral": 1, "maze": 1, "sigil": 1, "seal": 1, "dot": 1, "crescent": 1,
                                           "triad": 1, "polys": 1, "trigrams": 1, "compass": 1, "cross": 1, "flower": 1},
                     marks=0.25, offcentre=0.15, eccentric=0.08, rays=0.12, outer=0.12, crown=0.08),
    "polyad": dict(freq=4, n=[5, 6], style={"even": 2, "tiered": 1}, frame=["line", "double"], bands=(0, 2),
                   pool={T: 4, "dots": 1, "ticks": 1}, text=0.7, fig={"star": 1}, star_modes={"line": 2, "weave": 1},
                   nodes=0.3, topo="polyframe", center={"star": 2, "bullseye": 1, "symbol": 1}),
    "twin": dict(freq=5, n=[5, 6, 8, 4, 12], style={"tiered": 2, "fine": 1}, frame=["line", "double", "heavy2"],
                 bands=(1, 3), pool={T: 4, "ticks": 1, "dots": 1, "glyphs": 1}, text=0.8, fig={"star": 3, "none": 1},
                 star_modes={"line": 3, "weave": 1}, nodes=0.2, center={"symbol": 2, "sunburst": 1, "bullseye": 1},
                 topo="twin"),
    "trinity": dict(freq=2, n=[3, 6], style={"tiered": 2, "even": 1}, frame=["line", "double"], bands=(0, 2),
                    pool={T: 4, "dots": 1, "beads": 1}, text=0.7, fig={"star": 2, "none": 1},
                    star_modes={"line": 2, "weave": 1}, nodes=0.0, center={"symbol": 2, "star": 1, "bullseye": 1},
                    topo="trinity"),
}

# Each type keeps only its SIGNATURE layers strict; every other layer is a blend of the type's own pool (70%) and
# the broad freeform pool (30%), so a type keeps its character but no longer collides with itself so easily.
SIGNATURE = {
    "minimal": {"fig"}, "solomonic": {"frame", "text"}, "midchilda": {"n", "fig", "star_modes", "node_place"},
    "belka": {"n", "fig"}, "squared": {"n", "fig"}, "goetic": {"fig", "center"}, "tower": {"fig", "star_modes"},
    "clockwork": {"pool"}, "lens": {"fig"}, "tiles": {"fig", "glyph_frame"}, "ink": {"n", "fig", "style"},
    "celestial": {"glyph_src", "n", "fig"}, "scholarly": set(), "stave": {"fig", "center"},
    "rosette": {"star_modes", "fig"}, "alchemical": {"fig", "node_src"}, "trigram": {"glyph_src", "n"},
    "compass": {"fig"}, "lattice": {"fig"}, "sigil": {"fig", "center"}, "radiant": {"pool"},
    "freeform": {"n", "style", "frame", "pool", "fig", "center", "star_modes"}, "polyad": {"n", "fig"},
    "twin": set(), "trinity": set(),
}
BLEND = ("frame", "style", "pool", "center", "fig", "star_modes", "n")


def _as_weights(v):
    if isinstance(v, dict):
        return dict(v)
    out = {}
    for x in v:
        out[x] = out.get(x, 0) + 1
    return out


def _blend(own, broad, k=0.7):
    a, b = _as_weights(own), _as_weights(broad)
    sa, sb = sum(a.values()), sum(b.values())
    return {x: k * a.get(x, 0) / sa + (1 - k) * b.get(x, 0) / sb for x in set(a) | set(b)}


def _widen():
    broad = PRESETS["freeform"]
    for name, P in PRESETS.items():
        if name == "freeform":
            continue
        sig = SIGNATURE.get(name, set())
        for key in BLEND:
            if key in sig or key not in P:
                continue
            if key == "n" and P["n"] == [1] and name != "goetic":
                continue
            P[key] = _blend(P[key], broad[key])
        if "bands" not in sig and P["bands"][1] < 3:
            P["bands"] = (P["bands"][0], 3)
        for key in ("marks", "offcentre", "eccentric", "rays", "outer", "crown"):
            P.setdefault(key, broad[key] * 0.6)


_widen()

GLYPH_SRC = ["script", "alchem", "lib:hershey_astro", "lib:alchemical", "seal", "sparkle", "geomantic", "lib:hershey_misc",
             "star", "eye", "moon", "sun", "trigram"]
NODE_SRC = ["alchem", "lib:hershey_astro", "lib:alchemical", "seal", "script", "star", "sparkle", "eye", "bullseye"]


def pick(rng, table):
    if isinstance(table, dict):
        keys = list(table)
        return rng.choices(keys, weights=[table[k] for k in keys])[0]
    return rng.choice(table)


def lock(n, raw, lo=1):
    """Nearest multiple of n (>= lo·n)."""
    return n * max(lo, int(round(raw / n)))


def star_ks(n):
    return [k for k in range(1, (n + 1) // 2) if 2 * k != n] or [1]


def pick_k(rng, n, P):
    pref = (P.get("star_k") or {}).get(n)
    if pref:
        return rng.choice(pref)
    ks = [k for k in star_ks(n) if k >= 2] or [1]
    w = [3 if k == 2 else (2 if k == 3 else 1) for k in ks]
    if n in (3, 4) or rng.random() < 0.12:
        return 1
    return rng.choices(ks, w)[0]


# ---------------------------------------------------------------- sampler state

class S:
    def __init__(self, rng, P, n, scripts):
        self.rng, self.P, self.n, self.scripts = rng, P, n, scripts
        self.desc = {}


def script_label(scripts):
    g = scripts[0]
    lab = g["style"] if g["style"].startswith("lib:") else f"{g['style']}:{g.get('term', 'none')}"
    return lab + ("+2" if len(scripts) > 1 else "")


def _script_genome(rng, P):
    from . import script as script_mod
    allowed = P.get("scripts")
    libs = text_sets()
    if allowed:
        st = rng.choice(allowed)
        if st.startswith("lib:"):
            return {"style": st, "seed": rng.randrange(1 << 30), "sep": rng.choice(["dot", "cross", "space"])}
        g = script_mod.genome(rng)
        for _ in range(60):
            if g["style"] == st:
                break
            g = script_mod.genome(rng)
        return g
    g = script_mod.genome(rng, libs if rng.random() < 0.45 else ())
    if g["style"].startswith("lib:"):
        g["sep"] = rng.choice(["dot", "dot", "cross", "space", "diamond"])
    return g


# ---------------------------------------------------------------- bands

def band_params(st: S, kind, ri, ro, s, depth):
    rng, n, P = st.rng, st.n, st.P
    rm = (ri + ro) / 2
    w = ro - ri
    b = {"kind": kind, "ri": round(ri, 5), "ro": round(ro, 5)}
    circ = 2 * math.pi * rm
    if kind == "text":
        b["script"] = 1 if (len(st.scripts) > 1 and rng.random() < 0.5) else 0
        b["inward"] = rng.random() < (0.35 if depth == 0 and rm < 0.8 else 0.1)
        b["fill"] = rng.choice([0.56, 0.62, 0.68])
        b["tier"] = "hair" if w * s < 0.09 else "thin"
        if n > 1 and rng.random() < P.get("segments", 0.3):
            b["segments"] = rng.choice([d for d in (n, n * 2, n // 2) if d >= 2] or [n])
            b["brk_orn"] = rng.choice(["dot", "ring", "diamond", "sparkle", "star", "none"])
            b["brk_half"] = rng.choice([3.0, 5.0, 8.0])
            b["brk_phase"] = rng.choice([0.0, 180.0 / b["segments"]])
    elif kind == "inverted":
        b["script"] = 0
    elif kind in ("glyphs", "cells"):
        maxm = int(circ / (w * (1.25 if kind == "glyphs" else 1.0)))
        cands = [m for m in (n, 2 * n, 3 * n, 4 * n, 12, 8, 10) if m <= maxm and m % max(n, 1) == 0] or [n]
        b["m"] = rng.choice(cands)
        src = P.get("glyph_src") or GLYPH_SRC
        b["src"] = rng.choice(src)
        if b["src"] == "numeral":
            b["m"] = 12 if 12 <= maxm else b["m"]
        if b["src"] in ("zodiac",):
            b["m"] = 12 if 12 <= maxm else b["m"]
        if b["src"] == "trigram":
            b["m"] = 8
        if kind == "glyphs":
            b["frame"] = rng.choice(P.get("glyph_frame") or ["none", "none", "circle", "square", "diamond"])
            b["size"] = rng.choice([0.6, 0.7, 0.8])
            b["fixed"] = rng.random() < 0.25 and b["src"] not in ("numeral", "zodiac", "trigram", "geomantic")
        else:
            b["size"] = rng.choice([0.5, 0.6])
    elif kind == "roundels":
        maxm = int(circ / (w * 1.25))
        cands = [m for m in (n, 2 * n, 3 * n) if m <= maxm] or [n]
        b["m"] = rng.choice(cands)
        b["content"] = rng.choice(["script", "bullseye", "dot", "alchem", "lib:hershey_astro", "star", "sparkle", "none"])
        b["double"] = rng.random() < 0.35
        b["size"] = rng.choice([0.85, 0.95])
        b["fixed"] = rng.random() < 0.3
    elif kind == "ticks":
        pitch = rng.choice([0.018, 0.025, 0.035]) / max(s, 0.2) * min(1, s * 2)
        b["m"] = lock(n, circ / max(pitch, 0.012))
        b["major"] = rng.choice([0, b["m"] // n, 5 if b["m"] % 5 == 0 else 0, 2])
        b["side"] = rng.choice(["in", "in", "out", "mid"])
        b["minor"] = rng.choice([0.45, 0.6])
    elif kind == "dots":
        b["m"] = lock(n, circ / rng.choice([0.05, 0.07, 0.1]))
        b["size"] = rng.choice([0.2, 0.28])
        b["major"] = rng.choice([0, b["m"] // n if b["m"] // n > 1 else 0])
        b["hollow"] = rng.random() < 0.3
    elif kind == "beads":
        b["m"] = lock(n, circ / w * 0.5)
    elif kind == "loops":
        b["m"] = lock(n, circ / (w * rng.choice([0.7, 0.9])))
    elif kind == "zigzag":
        b["m"] = lock(n, circ / (w * rng.choice([1.2, 1.8])))
        b["fill"] = rng.random() < 0.35
    elif kind == "chevrons":
        b["m"] = lock(n, circ / (w * 1.4))
        b["dir"] = rng.choice([1, -1])
    elif kind in ("wave", "braid"):
        b["m"] = lock(n, circ / (w * rng.choice([2.5, 3.5])))
        if kind == "braid":
            b["kind"], b["strands"] = "wave", 2
    elif kind == "crenel":
        b["m"] = lock(n, circ / (w * 2.2))
    elif kind == "meander":
        b["m"] = lock(n, circ / (w * 1.5))
    elif kind == "scallop":
        b["m"] = lock(n, circ / (w * rng.choice([2.5, 4.0])))
        b["out"] = rng.random() < 0.7
        b["bold"] = rng.random() < 0.3
    elif kind == "orbit":
        b["m"] = rng.choice([n, 3, 2, 1]) if n > 1 else rng.choice([1, 2, 3])
        b["sym"] = rng.random() < 0.6
        b["body"] = rng.choice(["ring", "dot"])
    elif kind == "arcs":
        b["single"] = rng.random() < 0.4
        b["m"] = n if n > 1 else 3
        b["gapdeg"] = rng.choice([8, 15, 30])
        b["start"] = rng.uniform(0, 360)
        b["span"] = rng.uniform(120, 270)
    elif kind == "gear":
        b["m"] = lock(n, circ / (w * 1.6))
    elif kind == "petals":
        b["m"] = lock(n, circ / (w * rng.choice([1.0, 1.4])))
        b["layers"] = rng.choice([1, 1, 2])
    elif kind == "sparkles":
        b["m"] = lock(n, circ / (w * 2.2))
        b["k"] = rng.choice([4, 4, 8])
    elif kind == "diamonds":
        b["m"] = lock(n, circ / (w * 1.4))
        b["dot"] = rng.random() < 0.4
    elif kind == "crosses":
        b["m"] = lock(n, circ / (w * 2.2))
        b["style"] = rng.choice(["plain", "latin", "double"])
    elif kind == "ladder":
        b["m"] = lock(n, circ / (w * 0.6))
    elif kind == "triangles":
        b["m"] = lock(n, circ / (w * 1.3))
        b["out"] = rng.random() < 0.6
        b["fill"] = rng.random() < 0.3
        b["width"] = rng.choice([0.4, 0.6, 0.85])
    elif kind == "stars":
        b["m"] = lock(n, circ / (w * 2.0))
        b["k"] = rng.choice([5, 6, 7, 8])
    elif kind == "hatch":
        b["m"] = lock(n, circ / (w * 0.4))
        b["slant"] = rng.choice([1.0, 2.0])
        b["cross"] = rng.random() < 0.3
    elif kind == "vesica":
        b["m"] = lock(n, circ / (w * 3.0))
    elif kind == "keys":
        b["m"] = lock(n, circ / (w * 0.9), 2)
    return b


def band_label(b):
    """Visible identity of a band: its kind plus the sub-choice that changes how it reads."""
    k = b["kind"]
    if k == "text":
        seg = f":seg{b['segments']}:{b.get('brk_orn')}" if b.get("segments") else ""
        return "text" + seg + (":in" if b.get("inward") else "")
    if k in ("glyphs", "cells"):
        return f"{k}:{b.get('src')}:{b.get('frame', '')}"
    if k == "roundels":
        return f"roundels:{b.get('content')}" + (":2" if b.get("double") else "")
    if k == "ticks":
        return f"ticks:{b.get('side')}" + (":maj" if b.get("major") else "")
    if k == "dots":
        return "dots" + (":o" if b.get("hollow") else "") + (":maj" if b.get("major") else "")
    if k == "wave":
        return "braid" if b.get("strands") == 2 else "wave"
    if k == "zigzag":
        return "truss" if b.get("fill") else "zigzag"
    if k == "scallop":
        return "scallop:" + ("out" if b.get("out") else "in")
    if k == "orbit":
        return "orbit:" + ("sym" if b.get("sym") else "free")
    if k == "arcs":
        return "arc:single" if b.get("single") else "arcs"
    if k == "petals":
        return f"petals{b.get('layers', 1)}"
    if k == "triangles":
        return "triangles:" + ("out" if b.get("out") else "in") + (":fill" if b.get("fill") else "")
    if k == "crosses":
        return f"crosses:{b.get('style')}"
    if k == "diamonds":
        return "diamonds" + (":dot" if b.get("dot") else "")
    if k == "hatch":
        return "hatch" + (":x" if b.get("cross") else "")
    return k


def fig_label(f):
    k = f["kind"]
    if k == "star":
        return (f"star{f['n']}/{f['k']}:{f['mode']}" + (":ip" if f.get("inner_poly") else "")
                + (":pierce" if f.get("pierce") else ""))
    if k == "lens":
        return f"lens{f['n']}:{f.get('layers')}" + (":v" if f.get("vein") else "")
    if k == "spokes":
        return f"spokes{f['m']}:{f.get('levels')}"
    if k == "lattice":
        return f"lattice:{f.get('lat')}" + (f"+star{f['overlay']}" if f.get("overlay") else "")
    if k == "chain":
        return "chain" + "-".join(map(str, f["seq"]))
    if k == "compass":
        return f"compass{f['n']}" + (":pierce" if f.get("long", 0) > 1 else "")
    if k == "stave":
        sv = f["stave"]
        return f"stave{sv['n']}:{sv['mode']}:{sv['centre']}:" + ",".join(sorted({a["tip"] for a in sv["arms"]}))
    if k == "sigil":
        return f"sigil:{f.get('method')}" + (str(f.get("sq", "")) if f.get("method") == "kamea" else "") + f":{f.get('end')}"
    if k == "seal":
        from .symbols import seal_meta
        return "seal:" + seal_meta(f["gseed"])
    if k == "grid":
        return f"grid{f.get('k')}" + (":x" if f.get("diag") else "")
    if k == "triangles":
        return f"triangles{f.get('levels')}" + (":pair" if f.get("pair") else "")
    if k == "twist":
        return f"twist{f.get('n')}x{f.get('k')}"
    if k == "overlay":
        return "overlay:" + fig_label(f["star"]) + "+" + f["second"]
    return k


def center_label(c):
    k = c.get("kind", "none")
    if k == "symbol":
        return f"symbol:{c.get('src')}" + (":ring" if c.get("ring") else "")
    if k == "star":
        return f"star{c.get('n')}/{c.get('k')}"
    if k == "sunburst":
        return "sunburst:wavy" if c.get("wavy") else "sunburst"
    if k == "bullseye":
        return f"bullseye{c.get('k')}"
    if k == "polys":
        return f"polys{c.get('m')}"
    if k == "sigil":
        return f"sigil{c.get('sq')}"
    if k == "seal":
        from .symbols import seal_meta
        return "seal:" + seal_meta(c["gseed"])
    return k


def sample_bands(st: S, s, depth, r, core_min, nb, must=()):
    """Band stack from radius r inward. Returns (rings, bands, r_core, kinds)."""
    rng, P = st.rng, st.P
    rings, bands, kinds = [], [], []
    min_sep = MIN_SEP / s

    def add_ring(rr, style="line", tier="thin", **kw):
        for q in rings:
            if abs(q["r"] - rr) < min_sep:
                return False
        rings.append({"r": round(rr, 5), "style": style, "tier": tier, **kw})
        return True

    pool = dict(P["pool"])
    ntext = 0
    want_text = rng.random() < P.get("text", 0.5)
    want_text2 = rng.random() < P.get("text2", 0.15)
    breath_at = rng.randrange(max(nb, 1) + 1) if nb and rng.random() < 0.7 else -1
    todo = list(must)
    for i in range(nb):
        if todo:
            kind = todo.pop(0)
        elif want_text and ntext == 0 and (i == nb - 1 or rng.random() < 0.5):
            kind = "text"
        else:
            p = {k: v for k, v in pool.items() if not (kinds and kinds[-1] == k)}
            if ntext >= (2 if want_text2 else 1):
                p.pop("text", None)
            if not p:
                break
            kind = pick(rng, p)
        (lo, hi), (po, pi) = BAND[kind]
        width = rng.uniform(lo, hi)
        if kind == "text":
            width = max(width, MIN_TEXT / s)
            if P.get("big_text"):
                width = rng.uniform(0.14, 0.2)
        width = max(width, 0.022 / s)
        gap = rng.choice([0.0, 0.0, 0.012, 0.025]) / max(s, 0.3) * min(1.0, s * 1.5)
        if i == breath_at:
            gap += rng.uniform(0.04, 0.1)
        ro = r - gap
        ri = ro - width
        if ri < core_min:
            break
        if kind == "text" or rng.random() < po:
            add_ring(ro, "line", "thin" if kind == "text" else rng.choice(["thin", "hair"]))
        if kind == "text" or rng.random() < pi:
            add_ring(ri, "line", "thin" if kind == "text" else rng.choice(["thin", "hair"]))
        bands.append(band_params(st, kind, ri, ro, s, depth))
        kinds.append(bands[-1]["kind"] if kind != "braid" else "braid")
        ntext += kind == "text"
        r = ri
    return rings, bands, r, kinds


# ---------------------------------------------------------------- figure / nodes / centre

def sample_fig(st: S, rc, s, depth, tower_left=0):
    rng, P, n = st.rng, st.P, st.n
    kind = pick(rng, P["fig"]) if depth == 0 else rng.choice(["star", "none"])
    nf = P.get("fig_n", n) if n > 1 else 3
    f = {"kind": kind, "r": round(rc, 5)}
    if kind == "star":
        f["n"] = nf
        f["k"] = pick_k(rng, nf, P)
        f["mode"] = pick(rng, P.get("star_modes", {"line": 3, "weave": 1}))
        if f["mode"] in ("lanew", "merge") and (f["k"] > 2 or nf > 8):
            f["mode"] = "weave" if f["k"] > 1 else "lane"
        f["tier"] = rng.choice(["medium", "medium", "thin"])
        f["lw"] = round(rng.uniform(0.022, 0.04) / max(s, 0.25), 5)
        f["gap"] = round(0.016 / max(s, 0.25), 5)
        f["inner_poly"] = rng.random() < 0.3
        f["rot"] = rng.choice([0.0, 0.0, 180.0 / nf]) if depth == 0 else 0.0
    elif kind == "compass":
        f.update(n=n if n in (4, 8) else 8, long=rng.choice([rc, rc, 1.12, 1.18]) if depth == 0 else rc,
                 short=rc * rng.uniform(0.55, 0.8), w=rng.uniform(0.06, 0.11), base=rng.choice([0.0, rc * 0.2, rc * 0.3]),
                 tier=rng.choice(["thin", "medium"]))
    elif kind == "lens":
        f.update(n=n, r0=rng.choice([0.0, rc * 0.18, rc * 0.28, rc * 0.34]), bulge=rng.uniform(0.2, 0.34), layers=rng.choice([1, 2]),
                 len2=rng.uniform(0.5, 0.7), vein=rng.random() < 0.4)
    elif kind == "spokes":
        f.update(m=lock(n, rng.choice([12, 16, 24])), n=n, r0=rc * rng.uniform(0.2, 0.35), levels=rng.choice([1, 2, 3]))
    elif kind == "lattice":
        f.update(lat=rng.choice(["flower", "flower", "seed", "metatron", "fruit", "vesica", "trigrid", "rose"]),
                 rings=rng.choice([2, 3]), rot=0.0, m=rng.choice([6, 6, 8, 12]),
                 overlay=rng.choice([0, 0, 1, 2]))
    elif kind == "chain":
        seq = rng.choice([[3], [4], [3, 4], [4, 3], [3, 3], [6, 3], [5]])
        if n in (3, 4, 5, 6) and rng.random() < 0.5:
            seq[0] = n
        f.update(seq=seq, alt=rng.random() < 0.6, tier=rng.choice(["medium", "thin"]))
    elif kind == "stave":
        f["stave"] = stave_mod.sample(rng, n if n in (4, 6, 8) else 8)
        f["r0"] = rng.uniform(0.08, 0.16)
        f["tier"] = rng.choice(["medium", "thin"])
    elif kind == "sigil":
        f.update(method=rng.choice(["kamea", "kamea", "kamea", "wheel"]), sq=rng.choice([3, 4, 5, 6, 7, 8, 9]),
                 sym=rng.randrange(8), map=rng.choice(["pyth", "abc"]), end=rng.choice(["bar", "bar", "arrow", "circle"]),
                 backdrop=pick(rng, SIGIL_BACKDROP), rings=rng.choice([(6, 8, 12), (5, 8, 13), (3, 7, 12)]))
    elif kind == "seal":
        f["gseed"] = rng.randrange(1 << 30)
    elif kind == "grid":
        f.update(k=rng.choice([4, 5, 5]), size=rng.uniform(0.62, 0.72), diag=rng.random() < 0.4,
                 rot=rng.choice([0.0, 45.0]))
    elif kind == "triangles":
        f.update(levels=rng.choice([2, 3, 4]), pair=rng.random() < 0.4, shrink=rng.choice([0.5, 0.62]))
    elif kind == "twist":
        f.update(n=nf if nf >= 3 else 4, k=rng.choice([2, 3, 4]) if nf <= 6 else 2, ring=rng.random() < 0.5)
    elif kind == "overlay":
        n2 = nf if nf >= 5 else rng.choice([5, 6, 8])
        f["star"] = {"kind": "star", "n": n2, "k": pick_k(rng, n2, {}) if n2 >= 5 else 2, "r": round(rc, 5),
                     "mode": rng.choice(["line", "line", "weave"]), "tier": rng.choice(["medium", "thin"]),
                     "gap": round(0.016 / max(s, 0.25), 5), "rot": 0.0}
        f["second"] = rng.choice(["lens", "spokes", "twist", "rose"])
    return f


def sample_center(st: S, r, s, depth):
    rng, P, n = st.rng, st.P, st.n
    if r * s < 0.025:
        return {"kind": "none", "r": 0}
    kind = pick(rng, P["center"]) if depth == 0 else rng.choice(["symbol", "bullseye", "dot", "star", "none"])
    c = {"kind": kind, "r": round(r, 5)}
    if kind == "symbol":
        c["src"] = rng.choice(P.get("node_src") or NODE_SRC)
        c["ring"] = rng.random() < 0.4
    elif kind == "bullseye":
        c["k"] = rng.choice([1, 2, 3])
    elif kind == "sunburst":
        c["wavy"] = rng.random() < 0.35
        c["m"] = lock(n, rng.choice([8, 12, 16] if c["wavy"] else [12, 16, 24]))
    elif kind == "star":
        c["n"] = n if n >= 5 else rng.choice([5, 6])
        c["k"] = pick_k(rng, c["n"], {}) if c["n"] >= 5 else 2
        c["ring"] = rng.random() < 0.5
    elif kind == "rosette":
        c["m"] = n if n >= 4 else 6
        c["layers"] = rng.choice([1, 2])
    elif kind == "maze":
        c["diag"] = rng.random() < 0.5
    elif kind == "sigil":
        c.update(method="kamea", sq=rng.choice([3, 4, 5, 6]), sym=rng.randrange(8), map="pyth", end="bar",
                 backdrop=pick(rng, SIGIL_BACKDROP))
    elif kind == "seal":
        c["gseed"] = rng.randrange(1 << 30)
    elif kind == "polys":
        c["m"] = n if 3 <= n <= 8 else rng.choice([3, 4, 6])
        c["levels"] = rng.choice([2, 3, 4])
    return c


def sample_mini(st: S, s, content):
    """Node / satellite disc (depth >= 1): 1-2 rings, maybe a text band, then a content motif."""
    rng = st.rng
    rings = [{"r": 1.0, "style": "line", "tier": "thin"}]
    bands = []
    r = 1.0
    if s > 0.14 and rng.random() < 0.55:
        w = max(MIN_TEXT / s, 0.24)
        if w < 0.45:
            bands.append({"kind": "text", "ri": round(1 - w, 5), "ro": 1.0, "script": 0, "fill": 0.6,
                          "tier": "hair", "inward": False})
            rings.append({"r": round(1 - w, 5), "style": "line", "tier": "hair"})
            r = 1 - w
    elif rng.random() < 0.4 and 1 - MIN_SEP * 1.4 / s > 0.55:
        rr = 1 - MIN_SEP * 1.4 / s
        rings.append({"r": round(rr, 5), "style": "line", "tier": "hair"})
        r = rr
    core = {"r": round(r, 5), "fig": {"kind": "none", "r": r}, "nodes": None}
    if content == "star":
        nn = st.n if st.n >= 5 else rng.choice([5, 6])
        core["fig"] = {"kind": "star", "n": nn, "k": pick_k(rng, nn, {}) if nn >= 5 else 2, "r": round(r, 5),
                       "mode": "line", "tier": "thin", "rot": 0.0}
        core["center"] = {"kind": "none", "r": 0}
    elif content == "ringed":
        core["center"] = {"kind": "symbol", "src": rng.choice(st.P.get("node_src") or NODE_SRC), "r": round(r * 0.8, 5)}
    elif content == "spiral":
        core["center"] = {"kind": "spiral", "r": round(r * 0.9, 5), "turns": rng.choice([2, 3])}
    elif content == "bullseye":
        core["center"] = {"kind": "bullseye", "r": round(r * 0.85, 5), "k": rng.choice([1, 2])}
    else:
        core["center"] = {"kind": "symbol", "src": rng.choice(st.P.get("node_src") or NODE_SRC),
                          "r": round(r * 0.8, 5)}
    return {"rings": rings, "bands": bands, "core": core}


def sample_disc(st: S, s=1.0, depth=0, nb=None, core_min=None, tower=None):
    rng, P, n = st.rng, st.P, st.n
    rings = []
    frame = pick(rng, P["frame"]) if depth == 0 else rng.choice(["line", "double"])
    if depth == 0 and frame in ("line", "double") and rng.random() < 0.25:
        frame = rng.choice(["triple", "scallop", "teeth", "broken"])
    if frame == "triple":
        rings.append({"r": 1.0, "style": "triple", "tier": "thin", "gap": round(0.017 / s, 5)})
    elif frame == "scallop":
        rings.append({"r": 1.0, "style": "scallop", "tier": rng.choice(["medium", "thin"]), "m": lock(max(n, 1), 48),
                      "h": 0.035})
    elif frame == "teeth":
        rings.append({"r": 1.0, "style": "teeth", "tier": rng.choice(["medium", "thin"]), "m": lock(max(n, 1), 72),
                      "h": 0.03})
    elif frame == "broken":
        rings.append({"r": 1.0, "style": "broken", "tier": rng.choice(["heavy", "medium"]), "m": max(n, 4) if n < 5 else n,
                      "gapdeg": rng.choice([6.0, 12.0, 20.0])})
        rings.append({"r": round(1.0 - 0.02 / s, 5), "style": "line", "tier": "hair"})
    elif frame == "line":
        rings.append({"r": 1.0, "style": "line", "tier": rng.choice(["heavy", "medium"])})
    elif frame == "double":
        rings.append({"r": 1.0, "style": "double", "tier": rng.choice(["medium", "thin"]), "gap": round(0.02 / s, 5)})
    elif frame == "heavy2":
        rings.append({"r": 1.0, "style": "heavy2", "tier": "heavy", "gap": round(0.024 / s, 5)})
    if depth == 0:
        st.desc["frame"] = frame
    inner_line = min(q["r"] for q in rings) - (rings[0].get("gap", 0.0) * (2 if frame == "triple" else 1)
                                                if frame in ("double", "heavy2", "triple") else 0.0)
    r0 = inner_line - rng.choice([1.0, 1.4, 2.2]) * MIN_SEP / s
    if nb is None:
        nb = rng.randint(*P["bands"])
    cm = core_min if core_min is not None else rng.uniform(0.38, 0.55)
    rs, bands, rc, kinds = sample_bands(st, s, depth, r0, cm, nb, P.get("must", ()) if depth == 0 else ())
    for q in rs:
        if all(abs(q["r"] - x["r"]) >= MIN_SEP / s for x in rings):
            rings.append(q)
    if depth == 0 and tower is None:
        st.desc.update({f"b{i}": band_label(b) for i, b in enumerate(bands)})
        st.desc["nbands"] = len(kinds)
    # core ring (the figure touches it)
    gap = rng.choice([0.0, 0.015, 0.03]) / s * min(1, s * 1.2)
    rc = rc - gap
    fig = sample_fig(st, rc, s, depth)
    if fig["kind"] in ("star", "chain", "lens", "spokes", "stave", "lattice", "compass", "sigil", "none", "grid",
                       "triangles", "twist", "overlay"):
        if all(abs(rc - x["r"]) >= MIN_SEP / s for x in rings) and fig["kind"] != "none" or \
                (fig["kind"] == "none" and rng.random() < 0.5 and all(abs(rc - x["r"]) >= MIN_SEP / s for x in rings)):
            rings.append({"r": round(rc, 5), "style": "line", "tier": rng.choice(["thin", "medium"])})
    core = {"r": round(rc, 5), "fig": fig, "nodes": None}
    # pierce: the figure breaks out of the frame (Mid-Childa squares, compass spikes)
    if depth == 0 and fig["kind"] == "star" and rng.random() < P.get("pierce", 0.0):
        fig["r"] = round(rng.uniform(1.08, 1.2), 5)
        fig["clip"] = 0
        fig["pierce"] = True
        fig["mode"] = rng.choice(["lane", "merge", "lanew"]) if fig["k"] > 1 else "lane"
    # figure inner radius
    if fig["kind"] == "star":
        from .figures import star_inner
        inner = fig["r"] * star_inner(fig["n"], fig["k"]) * (math.cos(math.pi / fig["n"]) if fig["k"] > 1 else 1.0)
        if fig.get("pierce"):
            inner = rc * 0.55
        elif fig["mode"] not in ("line", "weave"):
            inner -= fig["lw"] * 1.2
    elif fig["kind"] == "chain":
        inner = rc
        for m in fig["seq"]:
            inner *= math.cos(math.pi / m)
    elif fig["kind"] in ("lens", "spokes", "compass"):
        inner = fig.get("r0") or fig.get("base") or rc * 0.2
        if fig["kind"] == "spokes":
            inner = fig["r0"]
    elif fig["kind"] in ("lattice", "grid"):
        inner = rc * rng.choice([0.0, 0.26, 0.34]) if depth == 0 else 0.0
        fig["hole"] = round(inner, 5)
    elif fig["kind"] == "triangles":
        inner = rc * (0.5 if fig["pair"] else fig["shrink"]) ** fig["levels"]
    elif fig["kind"] == "twist":
        inner = rc * math.cos(math.pi / fig["n"]) * 0.92 * 0.9
    elif fig["kind"] == "overlay":
        from .figures import star_inner
        sf = fig["star"]
        inner = rc * star_inner(sf["n"], sf["k"]) * (math.cos(math.pi / sf["n"]) if sf["k"] > 1 else 1.0)
        inner *= {"lens": 0.25, "spokes": 0.3, "twist": 0.75, "rose": 0.0}[fig["second"]]
    elif fig["kind"] in ("stave", "sigil", "seal"):
        inner = 0.0
    else:
        inner = rc
    # nodes
    if n > 1 and fig["kind"] in ("star", "chain", "lens", "compass", "none", "twist", "triangles", "overlay", "lattice") \
            and rng.random() < P.get("nodes", 0.3) \
            and depth == 0:
        place = rng.choice(P.get("node_place") or ["vertex", "vertex", "inner", "mid", "frame"])
        if fig["kind"] == "none":
            place = "mid"
        if place == "inner" and not (fig["kind"] == "star" and fig["k"] > 1):
            place = "vertex"
        rr = {"vertex": fig.get("r", rc), "inner": inner / max(math.cos(math.pi / max(fig.get("n") or n, 3)), 0.3),
              "mid": rc, "frame": 1.0}[place]
        if fig["kind"] == "compass":
            rr = fig["short"]
        m = {"star": fig.get("n"), "lens": fig.get("n"), "compass": fig.get("n"), "twist": fig.get("n"),
             "triangles": 3, "lattice": 6, "overlay": fig.get("star", {}).get("n"),
             "chain": (fig.get("seq") or [n])[0]}.get(fig["kind"]) or n
        if place == "inner" and fig["kind"] != "star":
            place = "vertex"
        rn = rng.uniform(0.07, 0.13) * (0.6 if place == "inner" else 1.0)
        rn = max(rn, 0.045 / s)
        rn = min(rn, math.pi * rr / m * 0.7)
        if rn * s >= 0.035:
            content = rng.choice(P.get("node") or ["symbol", "ringed", "star", "bullseye", "symbol"])
            core["nodes"] = {"place": place, "m": m, "r": round(rn, 5), "rr": round(rr, 5), "content": content,
                             "vary": rng.random() < 0.6, "disc": sample_mini(st, s * rn, content)}
            st.desc["nodes"] = f"{place}:{content}:{m}"
    # tower: another disc inside the figure
    tw = P.get("tower")
    if tower is None and tw and depth == 0:
        tower = rng.randint(*tw) - 1
    if tower and fig["kind"] == "star" and inner * s > 0.18:
        sub = S(rng, P, n, st.scripts)
        sub.desc = st.desc
        sub_disc = sample_disc(sub, s * inner * 0.97, depth, nb=rng.choice([0, 1]) if rng.random() > P.get("tower_ring", 1)
                               else rng.choice([0, 1]), core_min=0.3, tower=tower - 1)
        if rng.random() > P.get("tower_ring", 1.0):
            sub_disc["rings"] = sub_disc["rings"][1:]
        core["inner"] = {"s": round(inner * 0.97, 5), "disc": sub_disc}
        core["center"] = {"kind": "none", "r": 0}
    else:
        cr = inner * rng.uniform(0.6, 0.85) if inner > 0 else 0.0
        if fig["kind"] == "none" and depth == 0:
            cr = inner * rng.uniform(0.55, 0.8)
        core["center"] = sample_center(st, cr, s, depth)
    if depth == 0 and "fig" not in st.desc:
        st.desc["fig"] = fig_label(fig)
    if depth == 0 and core.get("inner"):
        st.desc["tower"] = st.desc.get("tower", 0) + 1
    if depth == 0 and not core.get("inner") and "center" not in st.desc:
        st.desc["center"] = center_label(core["center"])
    return {"rings": rings, "bands": bands, "core": core}


# ---------------------------------------------------------------- topologies

def topo_concentric(st: S):
    return {"disc": sample_disc(st), "c": [0.0, 0.0], "s": 1.0, "rot": 0.0}, []


def topo_polyframe(st: S, m):
    """Belka triangle / square frame: lanes along the polygon, sub-circles on the vertices, a circle inside."""
    rng = st.rng
    R = 0.84 if m == 3 else 0.8
    rot = 0.0 if m == 3 and rng.random() < 0.6 else (180.0 if m == 3 else rng.choice([0.0, 45.0]))
    rv = rng.uniform(0.17, 0.24) if m == 3 else rng.uniform(0.15, 0.2)
    apothem = R * math.cos(math.pi / m)
    h = rng.uniform(0.035, 0.05)
    ins = (apothem - h) * rng.uniform(0.86, 0.95)
    extras = [{"type": "lanes", "m": m, "R": R, "h": round(h, 5), "rot": rot, "text": rng.random() < 0.75,
               "script": 0, "center_line": rng.random() < 0.2}]
    content = rng.choice(["star", "ringed", "bullseye", "symbol", "spiral"])
    vary = rng.random() < 0.4
    for i in range(m):
        from .canvas import polar
        x, y = polar(R, rot + i * 360 / m)
        disc = sample_mini(st, rv, content) if (vary or i == 0) else extras[-1]["disc"]
        extras.append({"type": "sat", "c": [round(x, 5), round(y, 5)], "s": round(rv, 5), "rot": rot + i * 360 / m,
                       "disc": disc})
    root_n = st.n
    st.n = (6 if rng.random() < 0.5 else 3) if m == 3 else (rng.choice([4, 8]) if m == 4 else rng.choice([m, 2 * m]))
    disc = sample_disc(st, s=ins, nb=rng.choice([0, 1, 1, 2]), core_min=0.36)
    st.n = root_n
    st.desc["topo"] = f"poly{m}:{content}"
    return {"disc": disc, "c": [0.0, 0.0], "s": round(ins, 5), "rot": rot}, extras


def topo_graph(st: S):
    """Scholarly node graph: a main circle and satellites of different sizes joined by straight links."""
    rng = st.rng
    ms = rng.uniform(0.5, 0.62)
    main_c = (0.0, 0.0)
    disc = sample_disc(st, s=ms, nb=rng.randint(1, 3))
    extras = []
    k = rng.randint(3, 7)
    placed = []
    from .canvas import polar
    tries = 0
    while len(placed) < k and tries < 200:
        tries += 1
        rs = rng.uniform(0.1, 0.24)
        a = rng.uniform(0, 360)
        d = rng.uniform(ms + rs * 0.6, 1.05 - rs)
        x, y = polar(d, a)
        if math.hypot(x, y) + rs > 1.08:
            continue
        if any(math.hypot(x - px, y - py) < rs + pr + 0.04 for px, py, pr in placed):
            continue
        placed.append((x, y, rs))
    for x, y, rs in placed:
        content = rng.choice(["star", "ringed", "bullseye", "symbol", "spiral"])
        extras.append({"type": "sat", "c": [round(x, 5), round(y, 5)], "s": round(rs, 5), "rot": rng.uniform(0, 360),
                       "disc": sample_mini(st, rs, content)})
        extras.append({"type": "link", "p0": [0.0, 0.0], "p1": [round(x, 5), round(y, 5)], "tier": "hair",
                       "r0": ms})
    for i in range(len(placed) - 1):
        if rng.random() < 0.4:
            a, b = placed[i], placed[i + 1]
            extras.append({"type": "link", "p0": [a[0], a[1]], "p1": [b[0], b[1]], "tier": "hair", "r0": 0})
    if rng.random() < 0.6:
        extras.append({"type": "arc", "r": round(ms + rng.uniform(0.04, 0.08), 5), "a0": rng.uniform(0, 360),
                       "span": rng.uniform(120, 260), "w": rng.choice([0.012, 0.018])})
    if rng.random() < 0.5:
        extras.append({"type": "orbit", "r": round(rng.uniform(ms + 0.1, 0.95), 5)})
    st.desc["topo"] = f"graph{len(placed)}"
    return {"disc": disc, "c": [round(main_c[0], 5), round(main_c[1], 5)], "s": round(ms, 5), "rot": 0.0}, extras


def topo_twin(st: S):
    """Two full circles overlapping off-centre (the second sits on top: sun and moon)."""
    rng = st.rng
    a = rng.uniform(0, 360)
    from .canvas import polar
    s1 = rng.uniform(0.62, 0.72)
    s2 = rng.uniform(0.38, 0.5)
    c1 = polar(1.0 - s1, a + 180)
    c2 = polar(1.0 - s2, a)
    disc = sample_disc(st, s=s1)
    sub = S(rng, st.P, rng.choice([st.n, 3, 4, 5, 6]), st.scripts)
    sub.desc = {}
    d2 = sample_disc(sub, s=s2, nb=rng.choice([0, 1, 2]))
    extras = [{"type": "sat", "c": [round(c2[0], 5), round(c2[1], 5)], "s": round(s2, 5), "rot": 0.0, "disc": d2}]
    st.desc["topo"] = "twin:" + sub.desc.get("fig", "none").split(":")[0]
    return {"disc": disc, "c": [round(c1[0], 5), round(c1[1], 5)], "s": round(s1, 5), "rot": 0.0}, extras


def topo_trinity(st: S):
    """Three circles around a small central one, inside a thin binding ring."""
    rng = st.rng
    from .canvas import polar
    s3 = rng.uniform(0.3, 0.37)
    d = 1.0 - s3
    rot = rng.choice([0.0, 180.0])
    same = rng.random() < 0.6
    extras = [{"type": "orbit", "r": round(d, 5)}]
    first = None
    for i in range(3):
        sub = S(rng, st.P, st.n, st.scripts)
        sub.desc = {}
        dd = sample_disc(sub, s=s3, nb=rng.choice([0, 1])) if (not same or first is None) else first
        first = first or dd
        x, y = polar(d, rot + i * 120)
        extras.append({"type": "sat", "c": [round(x, 5), round(y, 5)], "s": round(s3, 5), "rot": rot + i * 120,
                       "disc": dd})
    sc = rng.uniform(0.75, 0.95) * (d - s3)
    disc = sample_disc(st, s=sc, nb=rng.choice([0, 1]))
    st.desc["topo"] = "trinity:" + ("same" if same else "mixed")
    return {"disc": disc, "c": [0.0, 0.0], "s": round(sc, 5), "rot": 0.0}, extras


def modifiers(st: S, root, extras):
    rng, P, n = st.rng, st.P, st.n
    mods = []
    if rng.random() < P.get("offcentre", 0.12) and not any(e["type"] == "sat" for e in extras):
        from .canvas import polar
        a = rng.choice([rng.uniform(0, 360), 45.0, 315.0, 135.0])
        rs = rng.uniform(0.16, 0.26)
        x, y = polar(1.0 - rs * rng.uniform(0.0, 0.6), a)
        extras.append({"type": "sat", "c": [round(x, 5), round(y, 5)], "s": round(rs, 5), "rot": 0.0,
                       "disc": sample_mini(st, rs, rng.choice(["ringed", "star", "bullseye", "symbol"]))})
        mods.append("offcentre")
    if rng.random() < P.get("marks", 0.22) and root["s"] == 1.0 and not any(e["type"] == "lanes" for e in extras):
        extras.append({"type": "marks", "kind": rng.choice(["spike", "glyph", "dot", "triangle", "sparkle"]),
                       "m": n if n > 1 else rng.choice([4, 8]), "r": round(1.0 + rng.uniform(0.04, 0.08), 5),
                       "size": round(rng.uniform(0.04, 0.07), 5)})
        mods.append("marks:" + extras[-1]["kind"])
    if rng.random() < P.get("eccentric", 0.05) and root["s"] == 1.0:
        k = rng.choice([1, 2, 3])
        for i in range(k):
            extras.append({"type": "ecc", "r": round(rng.uniform(0.35, 0.6), 5), "off": round(rng.uniform(0.1, 0.25), 5),
                           "a": rng.uniform(0, 360)})
        mods.append(f"ecc{k}")
    if root["s"] == 1.0:
        for key, kinds in (("rays", ["short", "long", "alt"]), ("outer", ["ring", "dotted", "dashed"]),
                           ("crown", ["arcs", "points"])):
            if rng.random() < P.get(key, 0.0):
                extras.append({"type": key, "kind": rng.choice(kinds), "m": lock(max(n, 1), rng.choice([16, 24, 36])),
                               "r": round(rng.uniform(1.04, 1.1), 5)})
                mods.append(f"{key}:{extras[-1]['kind']}")
    st.desc["mods"] = ",".join(sorted(mods)) or "none"
    d = root["disc"]
    ideas = len(d["bands"]) + bool(d["core"].get("nodes")) + (d["core"]["fig"]["kind"] != "none")         + bool(d["core"].get("inner")) + (d["core"].get("center", {}).get("kind", "none") not in ("none", "dot"))         + len(mods) + len([e for e in extras if e["type"] in ("sat", "lanes")])
    st.desc["ideas"] = ideas


SYL_C = ["z", "r", "th", "v", "s", "m", "n", "l", "k", "b", "d", "g", "h", "x", "ph", "q", "t", "sh", "y"]
SYL_V = ["a", "e", "i", "o", "u", "ae", "ia", "ai", "o", "a"]
SYL_END = ["el", "on", "ath", "is", "iel", "ar", "oth", "um", "ax", "", "", ""]


def true_name(rng) -> str:
    """Pronounceable pseudo-name: the text a circle's sigil traces when the seed has too few letters."""
    k = rng.randint(2, 3)
    s = "".join(rng.choice(SYL_C) + rng.choice(SYL_V) for _ in range(k)) + rng.choice(SYL_END)
    return s.capitalize()


def sample(seed: int, text: str = "", preset: str | None = None) -> dict:
    rng = random.Random(seed)
    name = preset or pick(rng, {k: v["freq"] for k, v in PRESETS.items()})
    P = PRESETS[name]
    n = pick(rng, P["n"])
    style = pick(rng, P["style"])
    color = pick(rng, PALETTE)
    scripts = [_script_genome(rng, P)]
    if rng.random() < 0.3:
        scripts.append(_script_genome(rng, P))
    st = S(rng, P, n, scripts)
    st.desc.update({"preset": name, "n": n, "style": style, "script": script_label(scripts)})
    topo = P.get("topo", "concentric")
    if topo == "belka":
        root, extras = topo_polyframe(st, 3)
    elif topo == "square":
        root, extras = topo_polyframe(st, 4)
    elif topo == "graph":
        root, extras = topo_graph(st)
    elif topo == "polyframe":
        root, extras = topo_polyframe(st, n)
    elif topo == "twin":
        root, extras = topo_twin(st)
    elif topo == "trinity":
        root, extras = topo_trinity(st)
    else:
        root, extras = topo_concentric(st)
        st.desc["topo"] = "concentric"
    modifiers(st, root, extras)
    letters = sum(ch.isalpha() and ch.isascii() for ch in (text or ""))
    tname = text if letters >= 4 else true_name(rng)
    return {"v": GENERATOR_VERSION, "seed": seed, "text": text, "name": tname, "preset": name, "n": n, "color": color,
            "style": style, "W": WEIGHTS[style], "scripts": scripts, "detail": rng.randrange(1 << 40),
            "root": root, "extras": extras, "desc": st.desc}
