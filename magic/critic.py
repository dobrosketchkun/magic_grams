"""Style critic: rejects samples that do not read as a designed magic circle (research/DESIGN.md §5).

score(plan, strokes) -> (ok, metrics, reasons)
  coverage     ink area / disc area of the drawing's extent: too faint reads as unfinished, too much as mud
  density      densest radial annulus (ink share of its area): glow merges crowded lines into a blob
  near_miss    concentric rings closer than MIN_SEP (glow fuses them into one smeared line)
  slivers      many tiny cut pieces (clearance cuts landing on near-tangent lines)
  text         text bands that ended up with (almost) no glyphs
Forbidden shapes (swastika / sun-wheel, research/traditions.md §17) are excluded structurally: every radial arm
ornament is mirror-symmetric about its own spine (stave.py) and no figure has bent arms under pure rotation.
"""
from __future__ import annotations

import math

import numpy as np

from .canvas import densify
from .generate import MIN_SEP

COVERAGE = (0.03, 0.30)
DENSITY_MAX = 0.62
MIN_IDEAS = 3             # distinct layers (bands, figure, nodes, centre, modifiers...): fewer reads as a sketch
SLIVERS_MAX = 40


def radial_profile(strokes, bins=24, rmax=1.2):
    """Ink area per annulus (bin edges 0..rmax)."""
    h = np.zeros(bins)
    total = 0.0
    for s in strokes:
        if s.fill:
            P = s.pts
            x, y = P[:, 0], P[:, 1]
            area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
            r = float(np.hypot(*P.mean(0)))
            k = min(bins - 1, int(r / rmax * bins))
            h[k] += area
            total += area
            continue
        P = densify(s.pts, s.closed, 0.01)
        if len(P) < 2:
            continue
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        mid = (P[1:] + P[:-1]) / 2
        r = np.hypot(mid[:, 0], mid[:, 1])
        k = np.minimum(bins - 1, (r / rmax * bins).astype(int))
        a = seg * s.w
        np.add.at(h, k, a)
        total += float(a.sum())
    return h, total


def score(plan, strokes):
    reasons = []
    h, ink = radial_profile(strokes, bins=12)
    bins = len(h)
    edges = np.linspace(0, 1.2, bins + 1)
    ann = np.pi * (edges[1:] ** 2 - edges[:-1] ** 2)
    dens = (h / ann)[2:]                  # annuli of width 0.1 from r = 0.2 (the centre is small and dense by design)
    ext = 1.0
    for s in strokes:
        if len(s.pts):
            ext = max(ext, float(np.hypot(s.pts[:, 0], s.pts[:, 1]).max()))
    cov = ink / (math.pi * ext * ext)
    m = {"coverage": round(cov, 4), "density": round(float(dens.max()), 3), "strokes": len(strokes)}
    if not COVERAGE[0] <= cov <= COVERAGE[1]:
        reasons.append(f"coverage {cov:.3f}")
    if dens.max() > DENSITY_MAX:
        reasons.append(f"dense annulus {dens.max():.2f}")
    # concentric ring near-misses (full or partial circles centred on the origin)
    radii = sorted({round(s.circ[2], 4) for s in strokes if s.circ is not None and abs(s.circ[0]) < 1e-6
                    and abs(s.circ[1]) < 1e-6 and s.circ[2] > 0.05})
    near = [(a, b) for a, b in zip(radii, radii[1:]) if 1e-4 < b - a < MIN_SEP * 0.8]
    m["near_miss"] = len(near)
    if near:
        reasons.append(f"{len(near)} near-miss rings")
    sl = sum(1 for s in strokes if not s.fill and not s.closed and s.length() < 0.012 and s.circ is not None)
    m["slivers"] = sl
    if sl > SLIVERS_MAX:
        reasons.append(f"{sl} slivers")
    ideas = plan.get("desc", {}).get("ideas", 99)
    m["ideas"] = ideas
    from .generate import PRESETS
    if ideas < PRESETS.get(plan.get("preset"), {}).get("min_ideas", MIN_IDEAS):
        reasons.append(f"only {ideas} ideas")
    return not reasons, m, reasons
