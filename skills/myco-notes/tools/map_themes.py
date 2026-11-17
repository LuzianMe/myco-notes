"""map_themes: the colour themes of the notes map (note pages, index and the mycelium view). Standard library only.

One table, THEMES, defines every theme: the CSS variables of the pages, the CSS variables of the mycelium view and the view's node,
group and thread colours. The map builder and notes_graph turn it into CSS, a theme picker and a tiny script that applies the stored
choice before the first paint. "Auto" (the default) sets no data-theme attribute, so the prefers-color-scheme rules decide, exactly as
before themes existed; Light and Dark are the colours the map always had.

The choice is kept in the browser under the key myco-theme (localStorage, if allowed; read once from the older myco-graph-theme so a
light/dark choice made before survives). A URL parameter ?theme=<id> shows one theme without storing it.
"""
import json

KEY, OLD_KEY = "myco-theme", "myco-graph-theme"
SANS = "system-ui,sans-serif"
GRAPH_SANS = 'system-ui,-apple-system,"Segoe UI",sans-serif'
MONO = 'ui-monospace,"Cascadia Mono","DejaVu Sans Mono",Menlo,Consolas,monospace'
SERIF = 'Charter,"Iowan Old Style","Palatino Linotype",Georgia,serif'

# Light and dark: exactly the colours of the pages and of the view before themes existed (the view always had its own pair).
LIGHT_PAGE = dict(bg="#f4f6f8", panel="#ffffff", fg="#1c252c", muted="#5d6b76", line="#d3dadf", accent="#0b6e6e", code="#f1f4f6")
DARK_PAGE = dict(bg="#12171b", panel="#1a2126", fg="#e3e9ed", muted="#93a3ae", line="#2b363e", accent="#4fc3c3", code="#161c20")
LIGHT_GRAPH = dict(bg="#f1eee3", bg2="#fbf9f0", fg="#1c2923", muted="#5a6a62", panel="rgba(255,253,245,.92)", line="#d6d1bb", accent="#0b7a6c", halo="#f1eee3")
DARK_GRAPH = dict(bg="#0a0f0d", bg2="#12201a", fg="#e1ece6", muted="#8da39a", panel="rgba(13,22,18,.88)", line="#27382f", accent="#58e0c8", halo="#0a0f0d")

# Each theme: id, label, dark, font, page colours, view colours (None: taken from the page colours) and the view's palette:
# pal = vivid group colours (read order, plans, the project's areas), quiet = the method's record groups (logs, archive, inbox...),
# hypha = thread colour as "r,g,b", wilt = a note past its review date, text and halo = node labels.
# The view's style per theme: style = threads (smooth: the original curve; organic: hyphae; circuit; fractal: Matrix's lattice
# traces), nodes (orb by default; pixel = crystals, pad = glass pads), rings around hubs, hit = what a note does when a spike
# lands and in the replay (glow, flash, ...), glow = strength of the glows (1 = full).
THEMES = [
    dict(id="light", label="Light", dark=False, font=SANS, style="smooth", graph_font=GRAPH_SANS, page=LIGHT_PAGE, graph=LIGHT_GRAPH,
         pal=["#0f8f80", "#c27410", "#7a55d8", "#cc3d5d", "#5a991b", "#1b73c4", "#9e8814", "#c2582b", "#2d9a5e", "#a8399c", "#c2189e", "#3f56c4"],
         quiet=["#5f6f69", "#7a6f5a", "#665f80", "#7a5f66", "#557080", "#6b7a55"], hypha="30,105,88", wilt="#8f5f2d", text="#1c2923", halo="#f1eee3"),
    dict(id="dark", label="Dark", dark=True, font=SANS, style="smooth", graph_font=GRAPH_SANS, page=DARK_PAGE, graph=DARK_GRAPH,
         pal=["#4fe3cf", "#ffb454", "#b79cff", "#ff7f96", "#a6e86a", "#62beff", "#ecd77f", "#ff9d73", "#7fe0a0", "#e58cd9", "#ff6fd8", "#9fb4ff"],
         quiet=["#8a9a94", "#a39883", "#8f8aa6", "#9c8a8f", "#7f9aa6", "#98a37f"], hypha="140,232,205", wilt="#b9824a", text="#e1ece6", halo="#0a0f0d"),
    dict(id="mycelium", label="Mycelium", dark=True, font=SANS, rings="powder", hit="spores",
         page=dict(bg="#150d18", bg2="#241629", panel="#1e1323", fg="#efe6f1", muted="#b9a7be", line="#3d2b45", accent="#a6ec6c", code="#1a1020"),
         pal=["#a6ec6c", "#3fd6b8", "#ff9a3c", "#c79bff", "#ff6f86", "#e8df7a", "#5ec8ff", "#79d46f", "#ffb38a", "#f27fd0", "#c4d85c", "#9aa4ff"],
         quiet=["#948a9a", "#a1958a", "#9088a8", "#a08c96", "#86999c", "#9aa386"], hypha="150,226,140", wilt="#d08a4c", text="#efe6f1"),
    dict(id="fruit", label="Fruit", dark=False, font=SANS, nodes="berry",
         page=dict(bg="#fff4e8", bg2="#fffaf3", panel="#ffffff", fg="#2b1c2a", muted="#6c5266", line="#f0d6c8", accent="#a8174f", code="#fdebe0"),
         pal=["#b0185a", "#4c8a0d", "#c05a00", "#3a4fc0", "#7b3fa0", "#1f7a3a", "#b04020", "#5b3aa8", "#a01836", "#00756a", "#8a6a00", "#c2185b"],
         quiet=["#7d6c70", "#7a6c5c", "#6c6680", "#7d6670", "#5f7180", "#6c7a5c"], hypha="176,70,110", wilt="#9a5b20", text="#2b1c2a"),
    dict(id="matrix", label="Matrix", dark=True, font=MONO, style="fractal", nodes="pixel", hit="flash", tglow=.3,
         page=dict(bg="#020805", bg2="#07150c", panel="#06110a", fg="#a8ffbb", muted="#6fd486", line="#1c3d25", accent="#4dff7c", code="#051009"),
         pal=["#39ff6a", "#b6ff4d", "#4de8ff", "#7dffd6", "#d6ffa8", "#7fd8ff", "#b46cff", "#00ff9c", "#5fffe0", "#5fd9b0", "#c88cff", "#3fc8ff"],   # every third an electric cyan; two "Mystery Data" violets
         quiet=["#4f9a60", "#62904e", "#4c927e", "#6c966c", "#548a7c", "#7c975e"], hypha="80,255,120", wilt="#d8b02e", text="#a8ffbb"),
    dict(id="amber", label="Amber terminal", dark=True, font=MONO, style="circuit", nodes="pad", hit="flash",
         page=dict(bg="#1a1007", bg2="#26180a", panel="#22150a", fg="#ffc66b", muted="#dca357", line="#4a3317", accent="#ffdc94", code="#24170b"),
         pal=["#ffb000", "#ffd27a", "#8cc8ff", "#ffe9a8", "#e0a050", "#a6e0ff", "#f7b267", "#ff9f43", "#7fb0ff", "#dca441", "#ffcf66", "#b8d8ff"],   # every third an ice blue
         quiet=["#a8896a", "#a08e72", "#988066", "#a89474", "#94826e", "#a69472"], hypha="255,176,0", wilt="#ff6e40", text="#ffc66b"),
    dict(id="contrast", label="High contrast", dark=True, font=SANS, style="smooth", glow=.35,
         page=dict(bg="#000000", bg2="#000000", panel="#0b0b0b", fg="#ffffff", muted="#e6e6e6", line="#9a9a9a", accent="#ffd400", code="#161616"),
         pal=["#ffd400", "#00e5ff", "#ff5cff", "#7cff00", "#ff7a1a", "#ffffff", "#5cb0ff", "#ff4d6a", "#00ff99", "#c99cff", "#ffe680", "#66ffff"],
         quiet=["#c4c4c4", "#adadad", "#d4d4d4", "#b8b8b8", "#a3a3a3", "#dedede"], hypha="255,255,255", wilt="#ff9a1a", text="#ffffff"),
    dict(id="deepsea", label="Deep sea", dark=True, font=SANS, rings="bubbles", hit="bubbles",
         page=dict(bg="#04142a", bg2="#0a2445", panel="#0b1d38", fg="#e6f4ff", muted="#a6c6e2", line="#22406a", accent="#4fe3f7", code="#081a33"),
         # Okabe-Ito colours (lightened where they would be too dark on navy): told apart with the common forms of colour blindness
         pal=["#e69f00", "#56b4e9", "#2ccf9f", "#f0e442", "#ff7f50", "#cc79a7", "#9fe0ff", "#ffc266", "#a8e6c8", "#f5a8cb", "#d6ec8a", "#c9c9ff"],
         quiet=["#8297ad", "#929ca6", "#8c91b0", "#9c92a3", "#7e9eac", "#90a294"], hypha="79,227,247", wilt="#ff7f50", text="#e6f4ff"),
    dict(id="paper", label="Paper", dark=False, font=SERIF, style="smooth", nodes="ink", rings="ink", hit="ink", glow=.4,
         page=dict(bg="#f4ecd8", bg2="#fbf5e6", panel="#fbf6ea", fg="#3a2e21", muted="#685640", line="#dccfb0", accent="#8a431a", code="#efe3c8"),
         pal=["#8a431a", "#2f5d7c", "#6b4c9a", "#9b2d3a", "#4f6b2a", "#8c6200", "#2e6f61", "#7a3f6a", "#4f4f8a", "#8f5a3a", "#3f6f3f", "#a0522d"],
         quiet=["#7f7563", "#7d715c", "#76717f", "#80706f", "#6f7c76", "#7a785c"], hypha="120,90,50", wilt="#b05a20", text="#3a2e21"),
]
BY_ID = {t["id"]: t for t in THEMES}
OPTIONS = [("auto", "Auto (system)")] + [(t["id"], t["label"]) for t in THEMES]


def _rgba(hex_color, alpha):
    v = int(hex_color[1:], 16)
    return f"rgba({v >> 16 & 255},{v >> 8 & 255},{v & 255},{alpha})"


def graph_vars(t):
    """The mycelium view's CSS variables for a theme (light and dark have their own; the others derive them from the page colours)."""
    if t.get("graph"):
        return t["graph"]
    p = t["page"]
    return dict(bg=p["bg"], bg2=p["bg2"], fg=p["fg"], muted=p["muted"], panel=_rgba(p["panel"], .92), line=p["line"], accent=p["accent"], halo=p["bg"])


def _block(sel, t, values, font):
    return sel + "{color-scheme:" + ("dark" if t["dark"] else "light") + ";" + "".join(f"--{k}:{v};" for k, v in values.items()) + f"--font:{font}}}"


def _css(kind):
    page = kind == "page"
    vals = (lambda t: {k: v for k, v in t["page"].items() if k != "bg2"}) if page else graph_vars
    font = (lambda t: t["font"]) if page else (lambda t: t.get("graph_font", t["font"]))
    base, other = (BY_ID["light"], BY_ID["dark"]) if page else (BY_ID["dark"], BY_ID["light"])   # pages start light, the view dark
    out = [_block(":root", base, vals(base), font(base)),
           "@media (prefers-color-scheme:" + ("dark" if page else "light") + "){" + _block(":root:not([data-theme])", other, vals(other), font(other)) + "}"]
    out += [_block(f':root[data-theme="{t["id"]}"]', t, vals(t), font(t)) for t in THEMES]
    out.append("@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}")
    return "\n".join(out)


def page_css():
    """CSS variables of every theme for the note pages and the index (Auto: light, or dark when the system asks for it)."""
    return _css("page")


def graph_css():
    """CSS variables of every theme for the mycelium view (Auto: dark, or light when the system asks for it, as before)."""
    return _css("graph")


def graph_data():
    """The view's colours per theme, for its script: {id: {dark, pal, quiet, hypha, wilt, text, halo, font}}."""
    return {t["id"]: dict(dark=t["dark"], pal=t["pal"], quiet=t["quiet"], hypha=t["hypha"], wilt=t["wilt"], text=t["text"],
                          halo=t.get("halo") or graph_vars(t)["halo"], font=t.get("graph_font", t["font"]), style=t.get("style", "organic"), nodes=t.get("nodes", ""), rings=t.get("rings", "rings"), hit=t.get("hit", "glow"), glow=t.get("glow", 1), tglow=t.get("tglow", t.get("glow", 1))) for t in THEMES}


def head_script():
    """Applied in <head> before the first paint: ?theme=, else the stored choice (the older key once, as a fallback)."""
    ids = " ".join(i for i, _ in OPTIONS)
    return ("<script>(function(){var r=document.documentElement,ok=' " + ids + " ',t=null;"
            "try{t=new URLSearchParams(location.search).get('theme')}catch(e){}"
            "if(!t||ok.indexOf(' '+t+' ')<0){t=null;try{t=localStorage.getItem('" + KEY + "');"
            "if(t===null){var o=localStorage.getItem('" + OLD_KEY + "');if(o==='light'||o==='dark'){t=o;localStorage.setItem('" + KEY + "',o)}}}catch(e){t=null}}"
            "if(t&&t!=='auto'&&ok.indexOf(' '+t+' ')>=0)r.setAttribute('data-theme',t)})()</script>")


def picker(label_class=""):
    """A labelled <select> with every theme, and the script that applies and stores a choice (and follows a choice made in another
    tab). It tells the page with a 'myco-theme' event, so the mycelium view can recolour its nodes."""
    opts = "".join(f'<option value="{i}">{l}</option>' for i, l in OPTIONS)
    lab = f'<span class="{label_class}">Theme</span>' if label_class else "Theme "
    return (f'<label class="theme-pick" title="Colour theme">{lab}<select id="theme-pick">{opts}</select></label>'
            "<script>(function(){var s=document.getElementById('theme-pick'),r=document.documentElement;if(!s)return;"
            "function show(){s.value=r.getAttribute('data-theme')||'auto'}"
            "function set(t,keep){if(t==='auto')r.removeAttribute('data-theme');else r.setAttribute('data-theme',t);"
            "if(keep){try{localStorage.setItem('" + KEY + "',t)}catch(e){}}show();"
            "try{document.dispatchEvent(new Event('myco-theme'))}catch(e){}}"
            "show();s.addEventListener('change',function(){set(s.value,true)});"
            "window.addEventListener('storage',function(e){if(e.key==='" + KEY + "'&&e.newValue&&s.querySelector('option[value=\"'+e.newValue+'\"]'))set(e.newValue,false)})"
            "})()</script>")


def graph_json():
    return json.dumps(graph_data(), separators=(",", ":"))
