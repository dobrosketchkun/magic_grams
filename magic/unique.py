"""Uniqueness: salient descriptors + a min-distance issuance registry (same scheme as halo_forge).

A descriptor is the tuple of DISCRETE, visible choices the sampler made: preset, topology, order n, frame, the band
sequence split into per-position dimensions (b0, b1, ...), figure (family / {n/k} / drawing mode), nodes, centre,
script style, modifiers, weight style. Individual glyphs and text runs do NOT count (they would make every seed
trivially unique); only the script style does. Distance = weighted count of differing dimensions.

Registry.try_issue() accepts a candidate only if its distance to EVERY issued circle is >= min_dist. Lookup uses
multi-index hashing: dimensions are split into `min_dist` blocks; since all weights are >= 1, any pair with
weighted distance < min_dist differs in < min_dist dimensions and so agrees exactly on at least one block.
"""
from __future__ import annotations

from collections import defaultdict

HEAVY = {"preset", "topo", "fig", "n", "nodes", "center", "b0", "b1"}
IGNORED = {"nbands", "ideas"}
# Order matters only for lookup speed: blocks take every min_dist-th dimension, so the dims are listed from most to
# least varied, spreading the high-entropy ones over all blocks (otherwise one block of mostly-constant dims —
# topology, empty band slots — puts nearly every circle into one bucket and lookups turn linear).
DIMS = ("fig", "center", "b0", "script", "b1", "nodes", "preset", "n", "b2", "mods", "frame", "style",
        "b3", "tower", "topo", "b4", "b5")


def descriptor(desc: dict) -> tuple:
    return tuple((k, str(desc.get(k, "na"))) for k in DIMS if k not in IGNORED)


def weight(dim: str) -> int:
    return 2 if dim in HEAVY else 1


def distance(a: tuple, b: tuple) -> int:
    da, db = dict(a), dict(b)
    return sum(weight(k) for k in da.keys() | db.keys() if da.get(k, "na") != db.get(k, "na"))


class Registry:
    def __init__(self, min_dist: int = 4):
        self.min_dist = min_dist
        self.items: list[tuple] = []
        self.index: dict[tuple, list[int]] = defaultdict(list)

    def _blocks(self, desc: tuple):
        k = self.min_dist
        for b in range(k):
            yield (b, tuple(v for i, (_, v) in enumerate(desc) if i % k == b))

    def conflicts(self, desc: tuple) -> list[int]:
        seen, out = set(), []
        for key in self._blocks(desc):
            for j in self.index.get(key, ()):
                if j not in seen:
                    seen.add(j)
                    if distance(desc, self.items[j]) < self.min_dist:
                        out.append(j)
        return out

    def try_issue(self, desc: tuple) -> int | None:
        if self.conflicts(desc):
            return None
        i = len(self.items)
        self.items.append(desc)
        for key in self._blocks(desc):
            self.index[key].append(i)
        return i

    def __len__(self):
        return len(self.items)
