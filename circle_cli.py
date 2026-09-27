"""Magic circle generator command line.

  python circle_cli.py                          # one random circle -> circle_<seed>.svg and .png
  python circle_cli.py --seed 12345             # a specific circle (any text works: --seed Zarathiel)
  python circle_cli.py --count 20 -o out/       # 20 random circles into a folder
  python circle_cli.py --preset clockwork       # force a type (see --list)
  python circle_cli.py --seed 7 --svg-only --size 1024 --color "#ffcc66" --transparent
  python circle_cli.py --seed 7 --info          # print what the circle is made of (JSON)
  python circle_cli.py --seed 7 --json          # also write the vector description (.circle.json)
  python circle_cli.py --sheet 24 -o out/       # contact sheet of 24 random circles (sheet.png)
  python circle_cli.py --issue alice bob        # permanent unique circles per person (registry file)
"""
import argparse
import json
import os
import sys

from magic import api


def hex_to_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def write(rec, args, stem):
    os.makedirs(args.out, exist_ok=True)
    paths = []
    if not args.png_only:
        p = os.path.join(args.out, stem + ".svg")
        with open(p, "w", encoding="utf-8") as f:
            f.write(api.svg(rec, size=args.size, color=args.color,
                            background=None if args.transparent else args.background, glow=args.glow))
        paths.append(p)
    if not args.svg_only:
        p = os.path.join(args.out, stem + ".png")
        api.png(rec, p, size=args.size, color=args.color,
                background=None if args.transparent else hex_to_rgb(args.background), glow=args.glow)
        paths.append(p)
    if args.json:
        p = os.path.join(args.out, stem + ".circle.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(api.to_json(rec, args.color))
        paths.append(p)
    return paths


def sheet(args, count):
    from PIL import Image, ImageDraw
    T = 320
    cols = 6
    tiles = []
    for _ in range(count):
        s = api.random_seed()
        rec = api.circle_for(s, args.preset)
        im = api.png(rec, size=T, color=args.color, background=hex_to_rgb(args.background), glow=args.glow)
        ImageDraw.Draw(im).text((5, 4), f"{s} {rec['preset']}", fill=(170, 170, 185))
        tiles.append(im)
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (T * min(cols, len(tiles)), T * rows), hex_to_rgb(args.background))
    for i, t in enumerate(tiles):
        out.paste(t, ((i % cols) * T, (i // cols) * T))
    os.makedirs(args.out, exist_ok=True)
    p = os.path.join(args.out, "sheet.png")
    out.save(p)
    print(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate anime-style magic circles (SVG / PNG).")
    ap.add_argument("--seed", action="append", help="circle seed, any text (repeatable); default: random")
    ap.add_argument("--count", type=int, default=1, help="number of random circles when no --seed is given")
    ap.add_argument("--preset", help="force a circle type (see --list)")
    ap.add_argument("--list", action="store_true", help="list the circle types")
    ap.add_argument("-o", "--out", default=".", help="output folder (default: current folder)")
    ap.add_argument("--size", type=int, default=768, help="image size in pixels (default 768)")
    ap.add_argument("--color", help='circle colour instead of the seed colour: "#ff8800", "ff8800" or "#f80"')
    ap.add_argument("--background", default="#0a0a12", help="background colour (default #0a0a12)")
    ap.add_argument("--transparent", action="store_true", help="transparent background")
    ap.add_argument("--glow", type=float, default=1.0, help="glow radius multiplier (default 1.0)")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--svg-only", action="store_true")
    fmt.add_argument("--png-only", action="store_true")
    ap.add_argument("--json", action="store_true", help="also write the vector description (.circle.json)")
    ap.add_argument("--info", action="store_true", help="print the circle's composition as JSON instead of files")
    ap.add_argument("--sheet", type=int, metavar="N", help="write a contact sheet of N random circles")
    ap.add_argument("--issue", nargs="+", metavar="PERSON", help="issue permanent unique circles to these people")
    ap.add_argument("--registry", default="registry.jsonl", help="registry file for --issue")
    args = ap.parse_args(argv)
    if args.list:
        print("\n".join(api.presets()))
        return 0
    try:
        args.color = api.normalize_color(args.color)
        hex_to_rgb(api.normalize_color(args.background))
        if args.preset and args.preset not in api.presets():
            raise ValueError(f"unknown preset {args.preset!r}; one of: {', '.join(api.presets())}")
    except ValueError as e:
        ap.error(str(e))
    if args.sheet:
        sheet(args, args.sheet)
        return 0
    if args.issue:
        from magic.issue import Issuer
        iss = Issuer(args.registry)
        for person in args.issue:
            rec = api.from_plan(iss.issue(person)["plan"], seed=person)
            for p in write(rec, args, f"circle_{api.safe_name(person)}"):
                print(p)
        return 0
    seeds = args.seed or [api.random_seed() for _ in range(args.count)]
    for s in seeds:
        rec = api.circle_for(s, args.preset)
        if args.info:
            print(json.dumps(api.info(rec), ensure_ascii=False))
            continue
        for p in write(rec, args, f"circle_{api.safe_name(s)}"):
            print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
