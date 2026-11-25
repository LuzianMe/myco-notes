#!/usr/bin/env python3
"""contrast: WCAG 2 contrast ratios of every map theme (skills/myco-notes/tools/map_themes.py). Standard library only.

    python3 tests/contrast.py [--all]

Checks, for the note pages and index and for the mycelium view:
  text      body text (fg) and muted text on the background, the panels and code blocks: at least 4.5:1
  links     the accent colour (links, and the view's links in its panel) on the background and the panels: at least 4.5:1
  nodes     every group colour, quiet colour and the wilt colour on the view's background: at least 3:1 (large graphics, UI)
  labels    node label text on its halo: at least 4.5:1
  wiki      the wiki layout's own colours: text on the tint of the current note and of a hover (4.5:1), the warning colour against the panel and the page (3:1)
A translucent panel is blended over the background (and over the lighter centre of the view's gradient) before it is measured.
Prints the failures (--all: every ratio). Exit 0 when every theme passes, 1 otherwise.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "myco-notes", "tools"))
import map_themes  # noqa: E402

TEXT, GRAPHIC = 4.5, 3.0


rgba, over, lum, ratio = map_themes.rgba, map_themes.over, map_themes.lum, map_themes.ratio   # the same maths the wiki layout uses to warn about a project's own colours


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
    x = map_themes.wiki_extra(t)
    for fgk in ("fg", "accent"):
        out.append((f"wiki {fgk} on the tint of the current note", p[fgk], x["soft"], TEXT))
        out.append((f"wiki {fgk} on a hovered row", p[fgk], x["hover"], TEXT))
    out.append(("wiki muted on a hovered row", p["muted"], x["hover"], TEXT))
    out.append(("wiki muted on a selected search result", p["muted"], x["soft"], TEXT))
    for bgk in ("bg", "panel"):
        out.append((f"wiki warning mark on {bgk}", x["warn"], p[bgk], GRAPHIC))
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
