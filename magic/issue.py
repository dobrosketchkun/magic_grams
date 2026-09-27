"""Issue circles to people: deterministic per person, critic-approved, min-distance unique, FROZEN once issued.

    iss = Issuer("registry.jsonl", min_dist=4)
    rec = iss.issue("alice")          # -> dict(person, seed, plan, ...)

The registry stores the FULL plan (every structural choice + the detail seed), so later generator changes never
alter an issued circle: build(plan) redraws it exactly. The uniqueness index is rebuilt from stored descriptors.
"""
from __future__ import annotations

import hashlib
import json
import os

from .build import build
from .critic import score
from .generate import GENERATOR_VERSION, sample
from .unique import Registry, descriptor

MAX_ATTEMPTS = 400


def seed_for(person: str, attempt: int) -> int:
    h = hashlib.blake2b(f"{person}#{attempt}".encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") & ((1 << 62) - 1)


class Issuer:
    def __init__(self, path: str | None = None, min_dist: int = 4):
        self.path = path
        self.reg = Registry(min_dist)
        self.records: dict[str, dict] = {}
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    self.reg.try_issue(descriptor(rec["plan"]["desc"]))
                    self.records[rec["person"]] = rec

    def issue(self, person: str) -> dict:
        if person in self.records:
            return self.records[person]
        for attempt in range(MAX_ATTEMPTS):
            plan = sample(seed_for(person, attempt), text=person)
            desc = descriptor(plan["desc"])
            if self.reg.conflicts(desc):
                continue
            ok, _, _ = score(plan, build(plan))
            if not ok:
                continue
            self.reg.try_issue(desc)
            rec = {"person": person, "attempts": attempt + 1, "generator": GENERATOR_VERSION, "plan": plan}
            self.records[person] = rec
            if self.path:
                os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec
        raise RuntimeError(f"no unique circle found for {person!r} in {MAX_ATTEMPTS} attempts (space saturating)")
