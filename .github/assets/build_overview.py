#!/usr/bin/env python3
"""build_overview: write the README's "How it works" diagram as two SVG files (light and dark).

    python3 .github/assets/build_overview.py

Writes overview-light.svg and overview-dark.svg next to this script. Edit the texts and the layout here, not in the SVG files.
Standard library only.
"""
import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 960, 650
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "light": dict(text="#1f2328", muted="#59636e", box="#f6f8fa", line="#d0d7de", you="#ddf4ff", you_line="#54aeff",
                  agent="#dafbe1", agent_line="#4ac26b", notes="#fbefff", notes_line="#c297ff", guard="#fff8c5",
                  guard_line="#d4a72c", arrow="#59636e", bg="#ffffff"),
    "dark": dict(text="#e6edf3", muted="#9198a1", box="#151b23", line="#3d444d", you="#0c2d6b", you_line="#4493f8",
                 agent="#0f3a1f", agent_line="#3fb950", notes="#3b1f5c", notes_line="#ab7df8", guard="#3a2c00",
                 guard_line="#d29922", arrow="#9198a1", bg="#0d1117"),
}

# Columns: x, width
YOU_X, YOU_W = 20, 220
AG_X, AG_W = 290, 330
NO_X, NO_W = 670, 270
ROW_Y0, ROW_H, ROW_GAP = 78, 50, 14

INPUTS = [
    ("Work on your system", ["Checks the live system, updates the", "right notes and commits them"]),
    ("“Note that …” (also from a phone)", ["Saves it in this month's inbox;", "sorting into the notes comes later"]),
    ("Ask a question", ["Reads the note index, answers with file", "names, offers to keep a hard-won answer"]),
    ("Share a link or a manual", ["Keeps it as a source, as found, and", "proposes what it changes in the notes"]),
    ("Bring an old notes folder", ["Imports or adopts it, after a backup;", "links and structure are kept"]),
]

NOTES = [
    ("state.md", "master record: what runs now"),
    ("runbook.md", "how-tos and lessons"),
    ("one note per device", "or service, decision, plan"),
    ("inbox/", "quick notes"),
    ("sources/", "outside documents"),
    ("logs/  archive/", "history, never rewritten"),
    ("plans/review-*.md", "proposed fixes"),
]


def text(x, y, s, c, size=13, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{c}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'font-family="{FONT}">{escape(s)}</text>')


def box(x, y, w, h, fill, stroke, r=8):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'


def arrow(x1, y1, x2, y2, c):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="1.6" marker-end="url(#a)"/>'


def path_arrow(d, c):
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.6" marker-end="url(#a)"/>'


def build(t):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="How Myco Notes works: you work and talk to your agent; the agent keeps a notes repository up to date; '
         f'every commit is checked; you approve review proposals and read briefings and maps.">',
         f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
         f'<path d="M0,0 L10,5 L0,10 z" fill="{t["arrow"]}"/></marker></defs>',
         f'<rect x="0" y="0" width="{W}" height="{H}" rx="12" fill="{t["bg"]}"/>']   # own background: readable on any page
    # column headings
    o.append(text(YOU_X + YOU_W / 2, 40, "You", t["text"], 16, "bold", "middle"))
    o.append(text(YOU_X + YOU_W / 2, 58, "just keep working", t["muted"], 12, anchor="middle"))
    o.append(text(AG_X + AG_W / 2, 40, "Your agent + the Myco Notes skill", t["text"], 16, "bold", "middle"))
    o.append(text(AG_X + AG_W / 2, 58, "does the bookkeeping", t["muted"], 12, anchor="middle"))
    o.append(text(NO_X + NO_W / 2, 40, "Your notes", t["text"], 16, "bold", "middle"))
    o.append(text(NO_X + NO_W / 2, 58, "plain Markdown in a git repository", t["muted"], 12, anchor="middle"))
    # input rows
    for i, (you, agent) in enumerate(INPUTS):
        y = ROW_Y0 + i * (ROW_H + ROW_GAP)
        o.append(box(YOU_X, y, YOU_W, ROW_H, t["you"], t["you_line"]))
        o.append(text(YOU_X + 14, y + ROW_H / 2 + 4.5, you, t["text"], 13))
        o.append(arrow(YOU_X + YOU_W + 2, y + ROW_H / 2, AG_X - 4, y + ROW_H / 2, t["arrow"]))
        o.append(box(AG_X, y, AG_W, ROW_H, t["agent"], t["agent_line"]))
        o.append(text(AG_X + 14, y + 21, agent[0], t["text"], 13))
        o.append(text(AG_X + 14, y + 38, agent[1], t["text"], 13))
        o.append(arrow(AG_X + AG_W + 2, y + ROW_H / 2, NO_X - 4, y + ROW_H / 2, t["arrow"]))
    rows_bottom = ROW_Y0 + len(INPUTS) * (ROW_H + ROW_GAP) - ROW_GAP
    # notes column
    o.append(box(NO_X, ROW_Y0, NO_W, rows_bottom - ROW_Y0, t["notes"], t["notes_line"]))
    y = ROW_Y0 + 26
    for name, what in NOTES:
        o.append(text(NO_X + 16, y, name, t["text"], 13, "bold"))
        o.append(text(NO_X + 16, y + 16, what, t["muted"], 12))
        y += 37
    o.append(text(NO_X + 16, rows_bottom - 12, "every note starts with a one-line summary", t["muted"], 12))
    # guard bar
    gy = rows_bottom + 26
    o.append(box(AG_X, gy, NO_X + NO_W - AG_X, 50, t["guard"], t["guard_line"]))
    o.append(text(AG_X + 16, gy + 21, "On every commit:  a hook refuses passwords and keys  ·  the lint checks links, dates", t["text"], 13, "bold"))
    o.append(text(AG_X + 16, gy + 38, "and summaries  ·  git keeps every version, so nothing is lost, only superseded", t["text"], 13))
    # loop back to you
    ry = gy + 82
    o.append(box(AG_X, ry, AG_W, 56, t["agent"], t["agent_line"]))
    o.append(text(AG_X + 14, ry + 22, "Review: reads what changed and writes", t["text"], 13))
    o.append(text(AG_X + 14, ry + 40, "each fix as a numbered proposal", t["text"], 13))
    o.append(path_arrow(f"M{NO_X + NO_W / 2},{gy + 50} L{NO_X + NO_W / 2},{ry + 28} L{AG_X + AG_W + 4},{ry + 28}", t["arrow"]))
    o.append(box(YOU_X, ry, YOU_W, 56, t["you"], t["you_line"]))
    o.append(text(YOU_X + 14, ry + 22, "You answer: yes, no or", t["text"], 13))
    o.append(text(YOU_X + 14, ry + 40, "a change; only yes is applied", t["text"], 13))
    o.append(arrow(AG_X - 2, ry + 28, YOU_X + YOU_W + 4, ry + 28, t["arrow"]))
    vy = ry + 82
    o.append(box(AG_X, vy, AG_W, 56, t["box"], t["line"]))
    o.append(text(AG_X + 14, vy + 22, "Views: a briefing at each session start,", t["text"], 13))
    o.append(text(AG_X + 14, vy + 40, "the note index, a map, the mycelium view", t["text"], 13))
    o.append(path_arrow(f"M{NO_X + NO_W - 40},{gy + 50} L{NO_X + NO_W - 40},{vy + 28} L{AG_X + AG_W + 4},{vy + 28}", t["arrow"]))
    o.append(box(YOU_X, vy, YOU_W, 56, t["you"], t["you_line"]))
    o.append(text(YOU_X + 14, vy + 22, "You (or the next session)", t["text"], 13))
    o.append(text(YOU_X + 14, vy + 40, "start from what is true now", t["text"], 13))
    o.append(arrow(AG_X - 2, vy + 28, YOU_X + YOU_W + 4, vy + 28, t["arrow"]))
    o.append("</svg>")
    return "\n".join(o) + "\n"


def main():
    for name, t in THEMES.items():
        p = os.path.join(HERE, f"overview-{name}.svg")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(build(t))
        print("wrote", os.path.relpath(p))


if __name__ == "__main__":
    main()
