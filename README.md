# Magic Grams

Procedural generator of glowing magic circles as seen in anime, manga, manhwa and light novels: rings of
invented script, pentagrams and star towers, seals, sigils, clockwork dials, polygon arrays, twin and triple
circles.  https://dobrosketchkun.github.io/magic_grams/

A seed is any text (a number, a word, a name). Every seed gives one circle, and the same seed gives the same circle on the
command line, in Python and on the web page. A seed with letters is also the circle's name, and its sigil traces
those letters on a planetary magic square.

![30 generated circles, one per type plus five freeform: minimal star, Solomonic, square array, triangle array,
square frame, Goetic seal, star tower, clockwork, petal lens, tiled, ink seal, celestial, node graph, stave,
rosette, alchemical, trigram, compass, lattice, sigil, radiant, freeform, polygon array, twin circles and
trinity](docs/showcase.png)

*Each label is the seed and the type (`python circle_cli.py --seed show9 --preset tiles`).*

## Web page

`index.html` is a static page for GitHub Pages. It runs the Python generator in the browser with Pyodide (numpy
only), so there is no server.

- Random circle, circle by seed, and a type filter.
- The seed's own colour, or a custom one (picker, hex, swatches). Glow strength.
- Downloads: SVG, PNG (512–4096 px, dark or transparent) and vector JSON.
- Shareable links: `?seed=Zarathiel`, `&type=clockwork`, `&color=ff8800`, `&glow=1.5`.
- A gallery of random circles; click one to open it.

To publish, push the repo, then in GitHub **Settings → Pages** choose "Deploy from a branch", branch `main`, folder
`/ (root)`. The `.nojekyll` file must stay: without it GitHub Pages runs Jekyll, which drops `magic/__init__.py`.

To test locally, run `python -m http.server 8000`, then open http://localhost:8000/?seed=Zarathiel.

## Command line

```
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt

python circle_cli.py                         # one random circle -> circle_<seed>.svg + .png
python circle_cli.py --seed Zarathiel        # a specific circle (any text)
python circle_cli.py --count 20 -o out/      # 20 random circles
python circle_cli.py --preset clockwork      # force a type (--list shows them)
python circle_cli.py --seed 7 --color ff8800 --glow 1.5
python circle_cli.py --seed 7 --transparent --size 2048
python circle_cli.py --seed 7 --info         # what the circle is made of (JSON)
python circle_cli.py --seed 7 --json         # + vector description (.circle.json)
python circle_cli.py --sheet 24 -o out/      # contact sheet of 24 random circles
python circle_cli.py --issue alice bob       # permanent, mutually distinct circles per person (registry.jsonl)
```

## Python

```python
from magic import api
rec = api.circle_for("Zarathiel")               # {seed, preset, name, color, desc, plan, strokes, ...}
open("c.svg", "w").write(api.svg(rec, size=1024))
api.png(rec, "c.png", size=1024, background=None)   # transparent
open("c.json", "w").write(api.to_json(rec))     # polylines + widths, y up, circle radius 1
```

## How it works

A circle is sampled layer by layer:
- topology: concentric; triangle, square, pentagon or hexagon array; node graph; twin circles; trinity
- symmetry order
- frame
- a band stack, outside to inside
- an interior figure
- nodes
- a centre
- modifiers

There are 25 **types** (presets). Each type keeps only its signature layers strict. Every other layer blends the
type's own choices (70%) with the broad freeform pool (30%). The types keep their character, and the combinations
multiply across layers. This is the same approach as [halo_forge](https://dobrosketchkun.github.io/halo_forge/).

- **Frames:** single, double, heavy + hairline, triple, scalloped crest, toothed, broken at the symmetry points.
- **Bands:** 29 kinds.
  - Text in an invented or historical script. It can be segmented at the symmetry points, and can face inward.
  - Glyph rings: zodiac, numerals, trigrams, geomantic figures, alchemical symbols.
  - Roundels, graduated ticks, dots, beads, looped chains, truss, chevrons, braid with over/under weave, meander,
    scallops, zodiac-like cells, orbits with bodies, bold broken arcs, gear teeth, lotus petals, sparkles,
    inverted text (solid band with the letters knocked out), lozenge chains, crosses, ladders, triangle rows,
    small stars, hatching, lens chains, key frets, and breathing space.
- **Figures:**
  - star polygons and compounds {n/k}, drawn as single lines, woven lines, double lanes, interlaced lanes, or lanes
    whose crossings merge into one outline
  - star towers (star → inner circle → star …)
  - compass spikes that pierce the frame
  - lens petals, spokes with stained-glass arcs
  - flower / seed / fruit of life, Metatron's cube, circle grids, triangular grids, roses of circles
    (optionally with a star laid over them)
  - dōman-style square grids, interleaved triangle stacks, twisted polygon rosettes
  - overlays: a star plus petals, spokes, a twisted polygon or a rose
  - inscribed polygon ↔ circle chains
  - Icelandic-style radial staves
  - kamea and rose-wheel sigils
  - Goetia-style mirrored seals
- **Centres:** emblems and symbols, bullseyes, sunbursts, small stars, eyes, rosettes, spirals, mazes, yin-yang,
  sigils, seals, crescent with star, triads, concentric polygons, the eight trigrams, compass roses, crosses
  pattées, seeds of life.
- **Modifiers:** an off-centre satellite, marks, rays or crowns outside the frame, an outer halo ring, eccentric
  orbits.
- **Scripts:**
  - **Invented:** every circle may invent its own alphabet from a style genome (runic, ring-terminal, blocky maze,
    curly, angular, cursive, cell). Glyphs within one alphabet keep a minimum distance from each other, counting
    mirror images.
  - **Historical:** harvested alphabets (see below).
- **Sigils:** the circle's name, or a generated pronounceable name, is traced through one of Agrippa's seven
  planetary squares. A small circle marks the start, a bar the end, and a loop a repeated letter.
- **Line craft:**
  - Lines stop short of every node circle.
  - Text leaves room where a node or piercing spike crosses its band.
  - Counts lock to the symmetry order.
  - Band widths are uneven, with one breathing band, and there are 3–4 stroke-weight tiers.
- **Critic:** rejects samples that are too faint, crowded into one annulus, have near-touching rings (glow would
  fuse them) or too few ideas.
- **Rendering:**
  - The SVG uses a three-radius glow filter.
  - The PNG uses its own numpy/Pillow compositor, with additive glow and a tone-mapped white-hot core. CairoSVG
    would silently drop the blur.
  - Everything is line art, so every export is an exact vector at any size.
- **No swastika or sun-wheel shapes:** every radial ornament is mirror-symmetric about its own arm, and no figure
  has bent arms under pure rotation.

**How many?** A descriptor lists the visible structural choices: type, topology, order, frame, each band (kind +
visible sub-choice), figure, nodes, centre, tower depth, script style, modifiers and weight style. Colour and
individual glyphs are not counted. `magic.issue.Issuer` issues one circle per person, with a guaranteed minimum
descriptor distance to every other issued circle. It freezes the full plan in a registry, so later generator
changes never alter an issued circle.

Measured on generator `2026.09.28-6`, without colour, with the distance definition unchanged:
- Exact structural combinations: 200,000 samples gave 199,936 distinct descriptors, with only 67 colliding pairs.
  That puts the effective number of distinct combinations at about 300 million.
- The issuance registry, run on 120,000 samples, kept 117,195 clearly different circles (distance ≥ 3) and 110,854
  very different ones (distance ≥ 4). Acceptance at the end was still 96.3% and 89.0%.
  - Extrapolating the acceptance decay (issued / −ln acceptance) gives roughly 3 million circles at distance ≥ 3 and
    1 million at distance ≥ 4.
  - These are conservative: acceptance decays more slowly than this model assumes.
  - The previous generator (`-2`) gave about 0.5 million and 0.2 million by the same method.
- The scripts are `.ignore/scripts/measure_unique2.py`, `measure_pairs.py` and `measure_collisions.py`.

## Layout

| Path | What |
|---|---|
| `magic/api.py` | public entry: `circle_for(seed)`, `svg()`, `png()`, `to_json()` |
| `magic/generate.py` | sampler: 25 types over shared layers → a JSON plan |
| `magic/build.py` | plan → strokes (discs, nodes, towers, satellites, polygon lanes, marks) |
| `magic/canvas.py` | stroke primitives, similarity transforms, clearance cuts (numpy only) |
| `magic/bands.py`, `figures.py` | band vocabulary; figures and centres |
| `magic/script.py`, `symbols.py`, `sigil.py`, `stave.py` | alphabets and arc text; symbols and seals; kamea / wheel sigils; staves |
| `magic/critic.py`, `unique.py`, `issue.py` | style critic, descriptor distance, per-person issuance |
| `magic/render.py` | SVG with glow filter, PNG compositor |
| `magic/data/` | harvested glyph sets split by license, `CREDITS.md`, `OFL.txt` |
| `circle_cli.py`, `index.html` | command line and web page |

## Glyph licenses

Details are in `magic/data/CREDITS.md`.
- `glyphs_pd.json`: Hershey fonts (public domain; acknowledgement kept).
- `glyphs_ccby.json`: occult alphabets by J. H. Peterson (Theban, Malachim, Celestial, Transitus Fluvii, Magi,
  Chaldean, Enochian; CC BY 4.0, attribution required).
- `glyphs_ofl.json`: Runic, Old Turkic, Old Hungarian, Tifinagh, Glagolitic and alchemical symbols derived from
  Noto fonts (SIL OFL 1.1; the glyph data stays OFL).

Generated images are not restricted by these licenses.
