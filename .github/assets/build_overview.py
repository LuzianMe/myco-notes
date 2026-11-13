#!/usr/bin/env python3
"""build_overview: write the README's "How it works" diagram as two SVG files (light and dark).

    python3 .github/assets/build_overview.py

Writes overview-light.svg and overview-dark.svg next to this script. Edit the texts and the layout here, not in the SVG files.
The diagram: what you give -> the method (six rules) -> what you get, and underneath the loop that repeats every session.
Standard library only.
"""
import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 960, 640
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "light": dict(bg="#ffffff", text="#1f2328", muted="#59636e", you="#ddf4ff", you_line="#54aeff", method="#dafbe1",
                  method_line="#4ac26b", num="#1a7f37", get="#fbefff", get_line="#c297ff", loop="#f6f8fa", loop_line="#d0d7de",
                  arrow="#59636e"),
    "dark": dict(bg="#0d1117", text="#e6edf3", muted="#9198a1", you="#0c2d6b", you_line="#4493f8", method="#0f3a1f",
                 method_line="#3fb950", num="#56d364", get="#3b1f5c", get_line="#ab7df8", loop="#151b23", loop_line="#3d444d",
                 arrow="#9198a1"),
}

GIVE = [
    ("Changes you make", "to the system or the project"),
    ("Quick thoughts", "typed or dictated, also from a phone"),
    ("Questions", "“what changed on the router?”"),
    ("Links and manuals", "release notes, forum answers"),
    ("Your decisions", "yes, no or a change"),
]
RULES = [
    ("Check the real system before writing", "not memory, not a script's own “ok”"),
    ("One home per fact", "other notes point to it; links are checked"),
    ("Evidence and dates", "the command, the numbers, how to undo it"),
    ("Supersede, never delete", "git keeps every version of every note"),
    ("No secrets, ever", "a hook refuses them on every commit"),
    ("Nothing changes without your yes", "reviews arrive as numbered proposals"),
]
GET = [
    ("Notes that are true", "and say when they were checked"),
    ("Answers with their source", "the note, the document, the date"),
    ("A briefing every session", "what is current, open, waiting on you"),
    ("Any past date", "what the notes said back then"),
    ("A map of what connects", "backlinks and the mycelium view"),
    ("Nothing leaked, nothing lost", "plain Markdown in your own git"),
]
LOOP = [["You work or ask"], ["The agent checks", "the system live"], ["Writes it to", "the right note"],
        ["Checked and", "committed"], ["Next session starts", "from what is true"]]   # one list per box: its lines

GX, GW = 20, 220          # what you give
MX, MW = 290, 370         # the method
RX, RW = 710, 230         # what you get
TOP, AREA = 92, 396       # the three columns share this vertical band


def text(x, y, s, c, size=13, weight="normal", anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{c}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'font-family="{FONT}">{escape(s)}</text>')


def box(x, y, w, h, fill, stroke, r=8):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'


def line(x1, y1, x2, y2, c, end=True):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="1.6"'
            + (' marker-end="url(#a)"' if end else "") + "/>")


def stack(items, x, w, fill, stroke, t, bold=True):
    """Boxes spread evenly over the shared band; returns the y of each box's middle."""
    n, gap = len(items), 10
    h = (AREA - gap * (n - 1)) / n
    out, mids = [], []
    for i, (title, sub) in enumerate(items):
        y = TOP + i * (h + gap)
        out.append(box(x, y, w, h, fill, stroke))
        out.append(text(x + 14, y + h / 2 - 3, title, t["text"], 13, "bold" if bold else "normal"))
        out.append(text(x + 14, y + h / 2 + 14, sub, t["muted"], 12))
        mids.append(y + h / 2)
    return out, mids


def build(t):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="How Myco Notes works. What you give: changes, quick thoughts, questions, links and manuals, decisions. '
         f'The method: check the real system before writing; one home per fact; evidence and dates; supersede, never delete; '
         f'no secrets, ever; nothing changes without your yes. What you get: notes that are true, answers with their source, '
         f'a briefing every session, any past date, a map of what connects, nothing leaked or lost. Session after session: '
         f'you work or ask, the agent checks it live, writes it to the right note, it is checked and committed, and the next '
         f'session starts from what is true; now and then a review proposes fixes and you decide.">',
         f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
         f'<path d="M0,0 L10,5 L0,10 z" fill="{t["arrow"]}"/></marker></defs>',
         f'<rect x="0" y="0" width="{W}" height="{H}" rx="12" fill="{t["bg"]}"/>']   # own background: readable on any page
    for x, w, head, sub in ((GX, GW, "What you give", "just keep working"),
                            (MX, MW, "The method", "rules your agent follows; tools check what they can"),
                            (RX, RW, "What you get", "in plain Markdown and git")):
        o.append(text(x + w / 2, 42, head, t["text"], 17, "bold", "middle"))
        o.append(text(x + w / 2, 62, sub, t["muted"], 12, anchor="middle"))
    # what you give -> the method
    g, gm = stack(GIVE, GX, GW, t["you"], t["you_line"], t)
    o += g
    for y in gm:
        o.append(line(GX + GW + 2, y, MX - 4, y, t["arrow"]))
    # the method: one box, six numbered rules
    o.append(box(MX, TOP, MW, AREA, t["method"], t["method_line"], 10))
    step = AREA / len(RULES)
    for i, (rule, why) in enumerate(RULES):
        cy = TOP + step * i + step / 2
        o.append(f'<circle cx="{MX + 28}" cy="{cy:.1f}" r="13" fill="none" stroke="{t["num"]}" stroke-width="1.6"/>')
        o.append(text(MX + 28, cy + 5, str(i + 1), t["num"], 14, "bold", "middle"))
        o.append(text(MX + 52, cy - 3, rule, t["text"], 14, "bold"))
        o.append(text(MX + 52, cy + 14, why, t["muted"], 12))
    # the method -> what you get
    r, rm = stack(GET, RX, RW, t["get"], t["get_line"], t)
    o += r
    for y in rm:
        o.append(line(MX + MW + 2, y, RX - 4, y, t["arrow"]))
    # the loop underneath
    ly = TOP + AREA + 34
    o.append(text(20, ly, "Session after session", t["text"], 15, "bold"))
    o.append(text(196, ly, "the agent forgets between sessions; the notes do not", t["muted"], 12))
    by, bh, gap = ly + 14, 52, 18
    bw = (W - 40 - gap * (len(LOOP) - 1)) / len(LOOP)
    for i, s in enumerate(LOOP):
        x = 20 + i * (bw + gap)
        o.append(box(x, by, bw, bh, t["loop"], t["loop_line"]))
        lines = s
        for j, ln in enumerate(lines):
            o.append(text(x + bw / 2, by + bh / 2 + 5 + (j - (len(lines) - 1) / 2) * 16, ln, t["text"], 13, anchor="middle"))
        if i < len(LOOP) - 1:
            o.append(line(x + bw + 2, by + bh / 2, x + bw + gap - 3, by + bh / 2, t["arrow"]))
    # return arrow: from the last step back to the first, under the row
    x_first = 20 + bw / 2
    x_last = 20 + (len(LOOP) - 1) * (bw + gap) + bw / 2
    ry = by + bh + 26
    o.append(f'<path d="M{x_last:.1f},{by + bh + 2:.1f} L{x_last:.1f},{ry:.1f} L{x_first:.1f},{ry:.1f} L{x_first:.1f},{by + bh + 5:.1f}" '
             f'fill="none" stroke="{t["arrow"]}" stroke-width="1.6" marker-end="url(#a)"/>')
    o.append(f'<rect x="{W / 2 - 250:.1f}" y="{ry - 11:.1f}" width="500" height="22" fill="{t["bg"]}"/>')
    o.append(text(W / 2, ry + 5, "now and then: a review proposes fixes, and you say yes, no or a change", t["muted"], 12, anchor="middle"))
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
