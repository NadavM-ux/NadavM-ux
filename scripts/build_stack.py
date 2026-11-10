#!/usr/bin/env python3
"""Build the clickable tech-stack tiles for this profile README.

GitHub shows README images as flat pictures, so a link inside one big image cannot be clicked.
Each tool is therefore its own small animated SVG (light and dark) in assets/stack/, wrapped in a link.

Run from anywhere:  python3 scripts/build_stack.py
It rewrites assets/stack/ and the block between the stack markers in README.md.

To add a tool, add a line to GROUPS. Logos come from Simple Icons (CC0-1.0), pinned to SI_VERSION and
cached in scripts/.icons/. Label widths come from scripts/stack_widths.json (measured in Chrome); a new
label without a measurement gets an estimate.
"""
import html
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets" / "stack"
CACHE = ROOT / "scripts" / ".icons"
SI_VERSION = "16.36.0"
WIDTHS = json.loads((ROOT / "scripts" / "stack_widths.json").read_text())

GH = "https://github.com/NadavM-ux/"
REPLY22 = (GH + "reply22-public", "used in Reply22")
ML = (GH + "machine_learning_course_final_project", "used in my ML project")
LOOKFINDS = (GH + "lookfinds-website", "used in LookFinds")


def site(url):
    return (url, "official site")


# Row: (label shown, accessible name, tools).
# Tool: (name, Simple Icons slug or None, logo cell colour, (link, hover text), [monogram, monogram colour]).
GROUPS = [
    ("LANGUAGES", "Languages", [
        ("TypeScript", "typescript", "3178C6", REPLY22),
        ("JavaScript", "javascript", "F7DF1E", LOOKFINDS),
        ("Python", "python", "3776AB", ML),
        ("Java", "openjdk", "ED8B00", site("https://dev.java")),
        ("C++", "cplusplus", "00599C", (GH + "cpp-basics", "my C++ coursework")),
        ("C", "c", "A8B9CC", ("https://en.cppreference.com/w/c", "reference")),
        ("C#", None, "68217A", (GH + "clinicvets", "used in ClinicVets"), "C#", "FFFFFF"),
    ]),
    ("BACKEND & DB", "Backend and databases", [
        ("Node.js", "nodedotjs", "5FA04E", REPLY22),
        ("NestJS", "nestjs", "E0234E", REPLY22),
        ("FastAPI", "fastapi", "009688", (GH + "book-list", "used in Book List API")),
        ("PostgreSQL", "postgresql", "4169E1", REPLY22),
        ("MySQL", "mysql", "4479A1", site("https://www.mysql.com")),
        ("Redis", "redis", "FF4438", REPLY22),
    ]),
    ("FRONTEND", "Frontend", [
        ("React", "react", "61DAFB", REPLY22),
        ("Next.js", "nextdotjs", "000000", REPLY22),
        ("Tailwind CSS", "tailwindcss", "06B6D4", LOOKFINDS),
        ("HTML5", "html5", "E34F26", (GH + "devloops", "used in DevLoops pages")),
        ("CSS", "css", "663399", LOOKFINDS),
    ]),
    ("ML & DATA", "ML and data", [
        ("scikit-learn", "scikitlearn", "F7931E", ML),
        ("pandas", "pandas", "150458", ML),
        ("NumPy", "numpy", "013243", ML),
        ("OpenCV", "opencv", "5C3EE8", site("https://opencv.org")),
        ("Jupyter", "jupyter", "F37626", ML),
    ]),
    ("TOOLS", "Tools", [
        ("Git", "git", "F03C2E", (GH + "book-list", "Book List API, built to practise Git workflows")),
        ("GitHub Actions", "githubactions", "2088FF", REPLY22),
        ("Docker", "docker", "2496ED", REPLY22),
        ("Linux", "linux", "FCC624", site("https://www.kernel.org")),
        ("Claude Code", "claude", "D97757", site("https://claude.com/claude-code")),
    ]),
    ("CLOUD & EDGE", "Cloud and edge", [
        ("Vercel", "vercel", "000000", (GH + "lookfinds-website", "LookFinds is deployed on Vercel")),
        ("Cloudflare", "cloudflare", "F38020", REPLY22),
        ("Raspberry Pi", "raspberrypi", "A22846", site("https://www.raspberrypi.com")),
    ]),
    ("CREATIVE", "Creative", [
        ("Photoshop", None, "001E36", site("https://www.adobe.com/products/photoshop.html"), "Ps", "31A8FF"),
        ("Premiere Pro", None, "00005B", site("https://www.adobe.com/products/premiere.html"), "Pr", "9999FF"),
        ("After Effects", None, "00005B", site("https://www.adobe.com/products/aftereffects.html"), "Ae", "9999FF"),
        ("Blender", "blender", "E87D0D", site("https://www.blender.org")),
    ]),
]
THEMES = {
    "dark": dict(chip="#161b22", stroke="#30363d", text="#e6edf3", label="#8b949e", accent="#4493f8",
                 sheen="#ffffff", sheen_op=0.12),
    "light": dict(chip="#f6f8fa", stroke="#d0d7de", text="#1f2328", label="#59636e", accent="#0969da",
                  sheen="#0969da", sheen_op=0.10),
}
WORDMARKS = {"mysql", "scikitlearn"}  # logos with text in them need a bigger glyph to stay legible
CH, CELL, RX, GAP, PAD_L, PAD_R, LCOL = 32, 32, 6, 8, 10, 12, 122
TOP, BOTTOM = 2, 8  # room inside each image for the rise animation
H = TOP + CH + BOTTOM
ROW_PITCH = H + 5  # approximate rendered row height, used to time the light sweep across rows
SPEED = 0.641  # sweep speed in px per ms
SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
CELL_PATH = f"M6 .5H{CELL}V{CH - .5}H6A5.5 5.5 0 0 1 .5 {CH - 6}V6A5.5 5.5 0 0 1 6 .5Z"
RISE = ("@keyframes rise { from { opacity: 0; transform: translateY(6px); } "
        "to { opacity: 1; transform: translateY(0); } }")


def file_id(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("++", "pp").replace("#", "sharp").replace(".", "")).strip("-")


def glyph(slug):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{slug}.svg"
    if not path.exists():
        url = f"https://cdn.jsdelivr.net/npm/simple-icons@{SI_VERSION}/icons/{slug}.svg"
        path.write_bytes(urllib.request.urlopen(url, timeout=30).read())
    return re.search(r'<path d="([^"]+)"', path.read_text()).group(1)


def lum(hexc):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def glyph_colour(cell):
    l = lum(cell)
    return "#ffffff" if 1.05 / (l + 0.05) >= (l + 0.05) / (lum("1f2328") + 0.05) else "#1f2328"


def text_width(name):
    return WIDTHS[name] * 1.04 + 2 if name in WIDTHS else len(name) * 7.6 + 2


def tile_svg(theme, tool, x, row, col):
    t, e = THEMES[theme], html.escape
    name, slug, cell = tool[0], tool[1], tool[2]
    tw = text_width(name)
    w = round(CELL + PAD_L + tw + PAD_R)
    dist = w + 200
    sweep_pct = dist / SPEED / 9000 * 100
    sweep_delay = round(2200 + (x + 0.325 * row * ROW_PITCH) / SPEED)
    if slug:
        size = 22 if slug in WORDMARKS else 16
        off = (CELL - size) / 2
        logo = f'<path transform="translate({off:g} {off:g}) scale({size / 24:.4f})" fill="{glyph_colour(cell)}" d="{glyph(slug)}"/>'
    else:
        logo = f'<text class="m" x="{CELL / 2:g}" y="20.6" text-anchor="middle" fill="#{tool[5]}">{e(tool[4])}</text>'
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + GAP}" height="{H}" viewBox="0 0 {w + GAP} {H}" role="img" aria-label="{e(name)}">',
        f'  <title>{e(name)}</title>',
        f'  <!-- Logo from Simple Icons {SI_VERSION} (CC0-1.0) where available. Trademarks belong to their owners. -->',
        '  <style>',
        f'    .t {{ font: 500 13px {SANS}; fill: {t["text"]}; }}',
        f'    .m {{ font: 700 13px {SANS}; }}',
        f'    .tile {{ animation: rise .65s cubic-bezier(.2, .7, .2, 1) {100 + row * 80 + col * 45}ms both; }}',
        f'    {RISE}',
        f'    .sheen {{ animation: sweep 9s linear {sweep_delay}ms infinite; }}',
        f'    @keyframes sweep {{ 0% {{ transform: translateX(0); }} {sweep_pct:.2f}%, 100% {{ transform: translateX({dist}px); }} }}',
        '    @media (prefers-reduced-motion: reduce) { .tile { animation: none; } .sheen { display: none; } }',
        '  </style>',
        '  <defs>',
        '    <linearGradient id="g" x1="0" x2="1" y1="0" y2="0">',
        f'      <stop offset="0" stop-color="{t["sheen"]}" stop-opacity="0"/>',
        f'      <stop offset=".5" stop-color="{t["sheen"]}" stop-opacity="{t["sheen_op"]}"/>',
        f'      <stop offset="1" stop-color="{t["sheen"]}" stop-opacity="0"/>',
        '    </linearGradient>',
        f'    <clipPath id="c"><rect x="0" y="{TOP}" width="{w}" height="{CH}" rx="{RX}"/></clipPath>',
        '  </defs>',
        '  <g class="tile">',
        f'    <g transform="translate(0 {TOP})">',
        f'      <rect x=".5" y=".5" width="{w - 1}" height="{CH - 1}" rx="{RX - .5}" fill="{t["chip"]}"/>',
        f'      <path d="{CELL_PATH}" fill="#{cell}"/>',
        f'      {logo}',
        f'      <text class="t" x="{CELL + PAD_L + tw / 2:.1f}" y="20.6" text-anchor="middle">{e(name)}</text>',
        f'      <rect x=".5" y=".5" width="{w - 1}" height="{CH - 1}" rx="{RX - .5}" fill="none" stroke="{t["stroke"]}"/>',
        '    </g>',
        f'    <g clip-path="url(#c)"><g transform="skewX(-18)"><rect class="sheen" x="-175" y="-4" width="160" height="{H + 8}" fill="url(#g)"/></g></g>',
        '  </g>',
        '</svg>',
        '']), w + GAP


def row_svg(theme, label, row):
    t, e = THEMES[theme], html.escape
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{LCOL}" height="{H}" viewBox="0 0 {LCOL} {H}" role="img" aria-label="{e(label)}">',
        f'  <title>{e(label)}</title>',
        '  <style>',
        f'    .lbl {{ font: 600 10.5px {MONO}; letter-spacing: 1.4px; fill: {t["label"]}; }}',
        f'    .row {{ animation: rise .65s cubic-bezier(.2, .7, .2, 1) {100 + row * 80}ms both; }}',
        f'    {RISE}',
        '    @media (prefers-reduced-motion: reduce) { .row { animation: none; } }',
        '  </style>',
        f'  <g class="row"><rect x="0" y="{TOP + 13}" width="6" height="6" fill="{t["accent"]}"/>'
        f'<text class="lbl" x="14" y="{TOP + 20}">{e(label)}</text></g>',
        '</svg>',
        ''])


def picture(stem, alt):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/stack/{stem}-dark.svg">'
            f'<img alt="{html.escape(alt)}" src="assets/stack/{stem}-light.svg"></picture>')


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    written, rows = set(), []
    for row, (label, alt_name, tools) in enumerate(GROUPS):
        stem = f"row-{row + 1}"
        for theme in THEMES:
            (ASSETS / f"{stem}-{theme}.svg").write_text(row_svg(theme, label, row))
            written.add(f"{stem}-{theme}.svg")
        parts, x = [f'<a href="#tech-stack">{picture(stem, alt_name)}</a>'], LCOL
        for col, tool in enumerate(tools):
            fid = file_id(tool[0])
            for theme in THEMES:
                svg, width = tile_svg(theme, tool, x, row, col)
                (ASSETS / f"{fid}-{theme}.svg").write_text(svg)
                written.add(f"{fid}-{theme}.svg")
            href, why = tool[3]
            parts.append(f'<a href="{html.escape(href)}" title="{html.escape(f"{tool[0]}: {why}")}">{picture(fid, tool[0])}</a>')
            x += width
        print(f"  {label:13s} {x}px wide")
        rows.append("".join(parts))
    for stale in ASSETS.glob("*.svg"):
        if stale.name not in written:
            stale.unlink()
    block = ("<!-- stack:start (generated by scripts/build_stack.py) -->\n<p>\n" + "<br>\n".join(rows)
             + "\n</p>\n<!-- stack:end -->")
    readme = ROOT / "README.md"
    text = readme.read_text()
    new, n = re.subn(r"<!-- stack:start.*?<!-- stack:end -->", lambda _: block, text, flags=re.S)
    if n != 1:
        raise SystemExit("README.md needs exactly one <!-- stack:start --> ... <!-- stack:end --> block")
    readme.write_text(new)
    print(f"wrote {len(written)} images and the README block")


if __name__ == "__main__":
    main()
