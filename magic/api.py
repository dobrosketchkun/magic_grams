"""Public entry points: circle for a seed, SVG / PNG / vector JSON. Used by the CLI and the web page.

A seed is any text ("12345", "tralala", a name). It is hashed (BLAKE2b) into the sampler's number; "circle <seed>"
is the first critic-approved sample of a deterministic sequence derived from that hash, so every seed gives a
good-looking circle and the same seed gives the same circle everywhere (CLI, browser) for a GENERATOR_VERSION.
A seed with letters also becomes the circle's name: its sigil traces those letters.
"""
from __future__ import annotations

import hashlib
import json
import random

from .build import build
from .critic import score
from .generate import GENERATOR_VERSION, PRESETS, sample
from .render import extent, to_png, to_svg

MAX_SEED_LEN = 200
ATTEMPTS = 60


def normalize_seed(seed) -> str:
    key = str(seed).strip()
    if not key:
        raise ValueError("seed must not be empty")
    if len(key) > MAX_SEED_LEN:
        raise ValueError(f"seed must be at most {MAX_SEED_LEN} characters")
    return key


def sub_seed(seed, attempt: int, preset: str | None = None) -> int:
    key = f"{normalize_seed(seed)}#{attempt}" + (f"@{preset}" if preset else "")
    h = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big") & ((1 << 62) - 1)


def random_seed() -> str:
    return str(random.SystemRandom().randrange(1, 10 ** 12))


def normalize_color(color):
    """'#ff8800', 'ff8800', '#f80' or 'f80' -> '#ff8800'; None -> None (use the circle's own colour)."""
    if color is None or str(color).strip() == "":
        return None
    c = str(color).strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in c):
        raise ValueError(f"color must be a hex color like #ff8800, got {color!r}")
    return "#" + c.lower()


def safe_name(seed) -> str:
    s = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(seed))[:60]
    return s or "circle"


def presets() -> list[str]:
    return list(PRESETS)


def circle_for(seed, preset: str | None = None) -> dict:
    """Deterministic, critic-approved circle for a public seed (any text); optionally forced to one preset."""
    seed = normalize_seed(seed)
    if preset is not None and preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}; one of: {', '.join(PRESETS)}")
    first = None
    for attempt in range(ATTEMPTS):
        plan = sample(sub_seed(seed, attempt, preset), text=seed, preset=preset)
        strokes = build(plan)
        ok, metrics, reasons = score(plan, strokes)
        first = first or (plan, strokes, metrics)
        if ok:
            return _record(seed, attempt, plan, strokes, metrics)
    plan, strokes, metrics = first
    return _record(seed, -1, plan, strokes, metrics)


def from_plan(plan: dict, seed=None) -> dict:
    """Redraw a stored plan (issued / frozen circles)."""
    strokes = build(plan)
    return _record(seed if seed is not None else plan.get("text") or plan["seed"], 0, plan, strokes, {})


def _record(seed, attempt, plan, strokes, metrics):
    return {"seed": seed, "attempt": attempt, "generator": GENERATOR_VERSION, "preset": plan["preset"],
            "name": plan.get("name"), "color": plan["color"], "n": plan["n"], "desc": plan["desc"], "plan": plan,
            "metrics": metrics, "strokes": strokes}


def info(rec) -> dict:
    return {k: rec.get(k) for k in ("seed", "preset", "name", "n", "color", "generator", "attempt", "desc", "metrics")}


def svg(rec: dict, size: int = 512, color: str | None = None, background: str | None = None, glow: float = 1.0) -> str:
    return to_svg(rec["strokes"], normalize_color(color) or rec["color"], size, background, glow,
                  title=f"Magic circle {rec['seed']}", uid_seed=rec["seed"])


def png(rec: dict, path: str | None = None, size: int = 512, color: str | None = None,
        background=(10, 10, 18), glow: float = 1.0):
    """PNG via the numpy/Pillow compositor. background: RGB tuple, or None for transparent."""
    return to_png(rec["strokes"], path, normalize_color(color) or rec["color"], size, background, glow)


def to_json(rec: dict, color: str | None = None) -> str:
    """Vector description: every stroke as a polyline with width (model units, y up, circle radius 1)."""
    out = []
    for s in rec["strokes"]:
        item = {"pts": [[round(float(x), 5), round(float(y), 5)] for x, y in s.pts], "w": round(s.w, 5)}
        if s.closed:
            item["closed"] = True
        if s.fill:
            item["fill"] = True
        if s.erase:
            item["erase"] = True
        if s.circ is not None:
            item["circle"] = [round(v, 5) for v in s.circ]
        out.append(item)
    return json.dumps({"seed": rec["seed"], "preset": rec["preset"], "name": rec.get("name"),
                       "color": normalize_color(color) or rec["color"], "generator": rec["generator"],
                       "extent": round(extent(rec["strokes"]), 4), "strokes": out}, ensure_ascii=False)
