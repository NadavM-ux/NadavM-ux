#!/usr/bin/env python3
"""Build the tech-stack card for this profile README.

One animated SVG card, in light and dark versions, with a labelled row per category: square tiles with a
brand-colour logo cell, a diagonal fade-in and a slow light sweep. It is a single picture, so the layout scales
as one piece on any screen. GitHub cannot make parts of a README image clickable, so the whole card links to
the repositories tab.

Run from anywhere:  python3 scripts/build_stack.py
It writes assets/stack/stack-{light,dark}-<hash>.svg and rewrites the block between the stack markers in
README.md. File names carry a short hash of their content, so an edited card never shows stale.

To add a tool, add a line to GROUPS. Logos come from Simple Icons (CC0-1.0), pinned to SI_VERSION and cached in
scripts/.icons/. Label widths come from scripts/stack_widths.json (measured in Chrome); a new label without a
measurement gets an estimate. The script stops if a row gets too wide for the card.
"""
import hashlib
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
LINK = "https://github.com/NadavM-ux?tab=repositories"

# Row: (label shown, accessible name, tools).
# Tool: (name, Simple Icons slug or None, logo cell colour, [monogram, monogram colour]).
GROUPS = [
    ("LANGUAGES", "Languages", [
        ("TypeScript", "typescript", "3178C6"), ("JavaScript", "javascript", "F7DF1E"), ("Python", "python", "3776AB"),
        ("Java", "openjdk", "ED8B00"), ("C++", "cplusplus", "00599C"), ("C", "c", "A8B9CC"),
        ("C#", None, "68217A", "C#", "FFFFFF"),
    ]),
    ("BACKEND & DB", "Backend and databases", [
        ("Node.js", "nodedotjs", "5FA04E"), ("NestJS", "nestjs", "E0234E"), ("FastAPI", "fastapi", "009688"),
        ("PostgreSQL", "postgresql", "4169E1"), ("MySQL", "mysql", "4479A1"), ("Redis", "redis", "FF4438"),
    ]),
    ("FRONTEND", "Frontend", [
        ("React", "react", "61DAFB"), ("Next.js", "nextdotjs", "000000"), ("Tailwind CSS", "tailwindcss", "06B6D4"),
        ("HTML5", "html5", "E34F26"), ("CSS", "css", "663399"),
    ]),
    ("ML & DATA", "ML and data", [
        ("scikit-learn", "scikitlearn", "F7931E"), ("pandas", "pandas", "150458"), ("NumPy", "numpy", "013243"),
        ("OpenCV", "opencv", "5C3EE8"), ("Jupyter", "jupyter", "F37626"),
    ]),
    ("TOOLS", "Tools", [
        ("Git", "git", "F03C2E"), ("GitHub Actions", "githubactions", "2088FF"), ("Docker", "docker", "2496ED"),
        ("Linux", "linux", "FCC624"), ("Claude Code", "claude", "D97757"),
    ]),
    ("CLOUD & EDGE", "Cloud and edge", [
        ("Vercel", "vercel", "000000"), ("Cloudflare", "cloudflare", "F38020"), ("Raspberry Pi", "raspberrypi", "A22846"),
    ]),
    ("CREATIVE", "Creative", [
        ("Photoshop", None, "001E36", "Ps", "31A8FF"), ("Premiere Pro", None, "00005B", "Pr", "9999FF"),
        ("After Effects", None, "00005B", "Ae", "9999FF"), ("Blender", "blender", "E87D0D"),
    ]),
]
THEMES = {
    "dark": dict(chip="#161b22", stroke="#30363d", text="#e6edf3", label="#8b949e", accent="#4493f8",
                 sheen="#ffffff", sheen_op=0.12),
    "light": dict(chip="#f6f8fa", stroke="#d0d7de", text="#1f2328", label="#59636e", accent="#0969da",
                  sheen="#0969da", sheen_op=0.10),
}
WORDMARKS = {"mysql", "scikitlearn"}  # logos with text in them need a bigger glyph to stay legible
W, LCOL, CH, CELL, RX, GAPX, ROWGAP, TOP = 840, 122, 32, 32, 6, 8, 10, 6
PAD_L, PAD_R = 10, 12
SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
CELL_PATH = f"M6 .5H{CELL}V{CH - .5}H6A5.5 5.5 0 0 1 .5 {CH - 6}V6A5.5 5.5 0 0 1 6 .5Z"


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


def layout():
    placed, labels, y = [], [], TOP
    for row, (label, _, tools) in enumerate(GROUPS):
        labels.append((label, y, row))
        x = LCOL
        for col, tool in enumerate(tools):
            tw = text_width(tool[0])
            w = round(CELL + PAD_L + tw + PAD_R)
            placed.append((tool, x, y, w, tw, row, col))
            x += w + GAPX
        if x - GAPX > W - 2:
            raise SystemExit(f"Row {label} is {x - GAPX}px wide, over the {W - 2}px card. Move a tool to another row.")
        y += CH + ROWGAP
    return placed, labels, y - ROWGAP + TOP


def build(theme, placed, labels, height, alt):
    t, e = THEMES[theme], html.escape
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="{e(alt)}">',
           f'  <title>{e(alt)}</title>',
           f'  <!-- Logos from Simple Icons {SI_VERSION} (CC0-1.0). Trademarks belong to their owners. -->',
           '  <style>',
           f'    .t {{ font: 500 13px {SANS}; fill: {t["text"]}; }}',
           f'    .m {{ font: 700 13px {SANS}; }}',
           f'    .lbl {{ font: 600 10.5px {MONO}; letter-spacing: 1.4px; fill: {t["label"]}; }}',
           '    .chip, .row { animation: rise .65s cubic-bezier(.2, .7, .2, 1) both; }',
           '    @keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }',
           '    .sheen { animation: sweep 9s cubic-bezier(.45, 0, .25, 1) 2.2s infinite; }',
           '    @keyframes sweep { 0% { transform: translateX(0); } 26%, 100% { transform: translateX(1500px); } }',
           '    @media (prefers-reduced-motion: reduce) { .chip, .row { animation: none; } .sheen { display: none; } }',
           '  </style>',
           '  <defs>',
           '    <linearGradient id="sg" x1="0" x2="1" y1="0" y2="0">',
           f'      <stop offset="0" stop-color="{t["sheen"]}" stop-opacity="0"/>',
           f'      <stop offset=".5" stop-color="{t["sheen"]}" stop-opacity="{t["sheen_op"]}"/>',
           f'      <stop offset="1" stop-color="{t["sheen"]}" stop-opacity="0"/>',
           '    </linearGradient>',
           '    <clipPath id="cp">']
    out += [f'      <rect x="{x}" y="{y}" width="{w}" height="{CH}" rx="{RX}"/>' for (_, x, y, w, _, _, _) in placed]
    out += ['    </clipPath>', '  </defs>']
    for label, ly, row in labels:
        out.append(f'  <g class="row" style="animation-delay:{100 + row * 80}ms">'
                   f'<rect x="0" y="{ly + 13}" width="6" height="6" fill="{t["accent"]}"/>'
                   f'<text class="lbl" x="14" y="{ly + 20}">{e(label)}</text></g>')
    for tool, x, y, w, tw, row, col in placed:
        name, slug, cell = tool[0], tool[1], tool[2]
        out += [f'  <g transform="translate({x},{y})"><g class="chip" style="animation-delay:{100 + row * 80 + col * 45}ms">',
                f'    <rect x=".5" y=".5" width="{w - 1}" height="{CH - 1}" rx="{RX - .5}" fill="{t["chip"]}"/>',
                f'    <path d="{CELL_PATH}" fill="#{cell}"/>']
        if slug:
            size = 22 if slug in WORDMARKS else 16
            off = (CELL - size) / 2
            out.append(f'    <path transform="translate({off:g} {off:g}) scale({size / 24:.4f})" fill="{glyph_colour(cell)}" d="{glyph(slug)}"/>')
        else:
            out.append(f'    <text class="m" x="{CELL / 2:g}" y="20.6" text-anchor="middle" fill="#{tool[4]}">{e(tool[3])}</text>')
        out += [f'    <text class="t" x="{CELL + PAD_L + tw / 2:.1f}" y="20.6" text-anchor="middle">{e(name)}</text>',
                f'    <rect x=".5" y=".5" width="{w - 1}" height="{CH - 1}" rx="{RX - .5}" fill="none" stroke="{t["stroke"]}"/>',
                '  </g></g>']
    out += ['  <g clip-path="url(#cp)"><g transform="skewX(-18)">',
            f'    <rect class="sheen" x="-420" y="-20" width="160" height="{height + 40}" fill="url(#sg)"/>',
            '  </g></g>', '</svg>', '']
    return "\n".join(out)


def main():
    placed, labels, height = layout()
    alt = "Tech stack. " + " ".join(f"{alt_name}: {', '.join(tool[0] for tool in tools)}." for _, alt_name, tools in GROUPS)
    ASSETS.mkdir(parents=True, exist_ok=True)
    files = {}
    for theme in THEMES:
        svg = build(theme, placed, labels, height, alt)
        files[theme] = f"stack-{theme}-{hashlib.sha1(svg.encode()).hexdigest()[:8]}.svg"
        (ASSETS / files[theme]).write_text(svg)
    for stale in ASSETS.glob("*.svg"):
        if stale.name not in files.values():
            stale.unlink()
    block = ("<!-- stack:start (generated by scripts/build_stack.py) -->\n"
             f'<a href="{LINK}" title="See my repositories"><picture>\n'
             f'  <source media="(prefers-color-scheme: dark)" srcset="assets/stack/{files["dark"]}">\n'
             f'  <img alt="{html.escape(alt)}" src="assets/stack/{files["light"]}" width="{W}">\n'
             "</picture></a>\n<!-- stack:end -->")
    readme = ROOT / "README.md"
    new, n = re.subn(r"<!-- stack:start.*?<!-- stack:end -->", lambda _: block, readme.read_text(), flags=re.S)
    if n != 1:
        raise SystemExit("README.md needs exactly one <!-- stack:start --> ... <!-- stack:end --> block")
    readme.write_text(new)
    print(f"{len(placed)} tools in {len(labels)} rows, card {W}x{height}px: {files['light']}, {files['dark']}")


if __name__ == "__main__":
    main()
