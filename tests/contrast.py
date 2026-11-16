#!/usr/bin/env python3
"""contrast: WCAG 2 contrast ratios of every map theme (skills/myco-notes/tools/map_themes.py). Standard library only.

    python3 tests/contrast.py [--all]

Checks, for the note pages and index and for the mycelium view:
  text      body text (fg) and muted text on the background, the panels and code blocks: at least 4.5:1
  links     the accent colour (links, and the view's links in its panel) on the background and the panels: at least 4.5:1
  nodes     every group colour, quiet colour and the wilt colour on the view's background: at least 3:1 (large graphics, UI)
  labels    node label text on its halo: at least 4.5:1
A translucent panel is blended over the background (and over the lighter centre of the view's gradient) before it is measured.
Prints the failures (--all: every ratio). Exit 0 when every theme passes, 1 otherwise.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "myco-notes", "tools"))
import map_themes  # noqa: E402

TEXT, GRAPHIC = 4.5, 3.0


def rgba(c):
    c = c.strip()
    if c.startswith("#"):
        v = int(c[1:], 16)
        return (v >> 16 & 255, v >> 8 & 255, v & 255, 1.0)
    parts = c[c.index("(") + 1:c.index(")")].split(",")
    return (int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3]) if len(parts) > 3 else 1.0)


def over(top, under):
    """`top` (may be translucent) painted over the opaque colour `under`."""
    r, g, b, a = rgba(top)
    R, G, B, _ = rgba(under)
    return "#%02x%02x%02x" % tuple(round(x * a + y * (1 - a)) for x, y in ((r, R), (g, G), (b, B)))


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b, _ = rgba(c)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def checks(t):
    """[(what, foreground, background, minimum)] for one theme."""
    p, g = t["page"], map_themes.graph_vars(t)
    out = []
    for fgk in ("fg", "muted"):
        for bgk in ("bg", "panel", "code"):
            if fgk == "muted" and bgk == "code":
                continue
            out.append((f"page {fgk} on {bgk}", p[fgk], p[bgk], TEXT))
    for bgk in ("bg", "panel"):
        out.append((f"page link/accent on {bgk}", p["accent"], p[bgk], TEXT))
    for base in ("bg", "bg2"):
        panel = over(g["panel"], g[base])
        for fgk in ("fg", "muted", "accent"):
            out.append((f"view {fgk} on {base}", g[fgk], g[base], TEXT))
            out.append((f"view {fgk} on panel over {base}", g[fgk], panel, TEXT))
    for i, c in enumerate(t["pal"]):
        out.append((f"view group colour {i + 1}", c, g["bg"], GRAPHIC))
    for i, c in enumerate(t["quiet"]):
        out.append((f"view quiet colour {i + 1}", c, g["bg"], GRAPHIC))
    out.append(("view wilt colour", t["wilt"], g["bg"], GRAPHIC))
    out.append(("view label on halo", t["text"], t.get("halo") or g["halo"], TEXT))
    return out


def main():
    show_all = "--all" in sys.argv[1:]
    failed = 0
    for t in map_themes.THEMES:
        rows = [(w, f, b, m, ratio(f, b)) for w, f, b, m in checks(t)]
        bad = [r for r in rows if r[4] < r[3]]
        failed += len(bad)
        print(f"{t['id']:<9} {t['label']:<15} lowest text {min(r[4] for r in rows if r[3] == TEXT):5.2f}  lowest graphic "
              f"{min(r[4] for r in rows if r[3] == GRAPHIC):5.2f}  {'OK' if not bad else 'FAIL ' + str(len(bad))}")
        for w, f, b, m, r in (rows if show_all else bad):
            print(f"    {'FAIL' if r < m else 'ok  '} {w}: {f} on {b} = {r:.2f} (needs {m})")
    print(f"contrast: {len(map_themes.THEMES)} themes, {failed} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
