"""Harvested glyph sets (built by .ignore/scripts/build_glyphs.py; licenses in magic/data/CREDITS.md).

glyphs_pd.json    Hershey fonts (public domain; acknowledgement requested)
glyphs_ccby.json  J. H. Peterson occult alphabets (CC-BY 4.0)
glyphs_ofl.json   Noto-derived scripts and alchemical symbols (OFL-1.1)
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

DATA = os.path.join(os.path.dirname(__file__), "data")
FILES = ("glyphs_pd.json", "glyphs_ccby.json", "glyphs_ofl.json")


@lru_cache(maxsize=None)
def _all() -> dict:
    sets = {}
    for f in FILES:
        p = os.path.join(DATA, f)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                sets.update(json.load(fh))
    return sets


def _pairs(flat):
    return [(flat[i], flat[i + 1]) for i in range(0, len(flat) - 1, 2)]


def text_sets() -> list[str]:
    return sorted(k for k, v in _all().items() if v["role"] == "text")


def node_sets() -> list[str]:
    return sorted(k for k, v in _all().items() if v["role"] == "node")


@lru_cache(maxsize=None)
def text_set(name: str) -> list[dict]:
    """Glyphs in script format (baseline 0, cap height 1, x from 0)."""
    return [{"s": [_pairs(s) for s in g["s"]], "c": [], "w": max(g["w"], 0.12), "id": g["id"]}
            for g in _all()[name]["glyphs"]]


@lru_cache(maxsize=None)
def node_set(name: str) -> list[dict]:
    """Symbols in script format, unit box: x, y in [0, 1] (draw_glyph centres them)."""
    return [{"s": [[(x + 0.5, y + 0.5) for x, y in _pairs(s)] for s in g["s"]], "c": [], "w": 1.0, "id": g["id"]}
            for g in _all()[name]["glyphs"]]
