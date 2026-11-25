#!/usr/bin/env python3
"""record_media: record the README's animation and theme gallery from the demo notes.

    python3 .github/assets/record_media.py [--chromium PATH]

Builds the demo notes (examples/demo/build_demo.py) in a temporary folder, serves its map locally, and writes next to this script:
  mycelium.webp         the replay of the git history, then the view turning in 3D while it switches through the themes
  graph-themes.webp     a gallery of the themes, one tile each
  wiki-layout.webp      a note page of the wiki layout (build-notes-map.py --layout wiki), light and dark side by side
Needs Playwright for Python and Pillow (pip install playwright pillow); these are only for making the README's pictures, the kit
itself does not use them. --chromium points at a Chromium or headless-shell binary if Playwright's own is not installed.
"""
import argparse, functools, http.server, os, subprocess, sys, tempfile, threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
THEMES = ["mycelium", "matrix", "amber", "deepsea", "fruit", "paper", "contrast", "light", "dark"]
PROBE = "window.__turn=function(d,t){rot.y+=d;rot.x=t;spin.on=false;spin.vy=0;spin.last=performance.now()};"


def wiki_shot(a, demo, tmp, Image, sync_playwright):
    """One note page of the wiki layout in the Light and Dark themes, side by side (the tree, breadcrumbs, summary, links here, previous and next)."""
    wk = os.path.join(tmp, "wiki")
    subprocess.run([sys.executable, os.path.join(demo, "myco-notes", "tools", "build-notes-map.py"), "--root", demo, "--layout", "wiki", "--out", wk],
                   check=True, capture_output=True)
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=wk)
    h.log_message = lambda *x: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    page = f"http://127.0.0.1:{srv.server_address[1]}/p/myco-notes-entities-gateway.html"
    tiles = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=a.chromium) if a.chromium else p.chromium.launch()
        for th in ("light", "dark"):
            pg = b.new_page(viewport={"width": 1280, "height": 760})
            pg.goto(page + "?theme=" + th)
            pg.wait_for_timeout(800)
            tiles.append(Image.open(__import__("io").BytesIO(pg.screenshot())).convert("RGB").resize((720, 428), Image.LANCZOS))
        b.close()
    g = Image.new("RGB", (720 * 2 + 4, 428), (128, 128, 128))
    g.paste(tiles[0], (0, 0))
    g.paste(tiles[1], (724, 0))
    out = os.path.join(HERE, "wiki-layout.webp")
    g.save(out, quality=82)
    print("wrote", out, os.path.getsize(out) // 1024, "KB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chromium", default=None)
    ap.add_argument("--only", choices=("all", "wiki"), default="all", help="wiki: only wiki-layout.webp (the animation is a few MB and changes on every recording)")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="myco-media-")
    demo = os.path.join(tmp, "demo")
    subprocess.run([sys.executable, os.path.join(REPO, "examples", "demo", "build_demo.py"), demo], check=True, capture_output=True)
    mp = os.path.join(demo, "myco-notes", "map")
    wiki_shot(a, demo, tmp, Image, sync_playwright)
    if a.only == "wiki":
        return
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=mp)
    h.log_message = lambda *x: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/graph.html"
    frames, durs = [], []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=a.chromium) if a.chromium else p.chromium.launch()
        ctx = b.new_context(viewport={"width": 960, "height": 600}, device_scale_factor=1)
        ctx.route("**/graph.html*", lambda r, q=None: r.fulfill(body=r.fetch().text().replace("readTheme();resize();", PROBE + "readTheme();resize();", 1),
                                                         headers={"content-type": "text/html"}))
        ctx.add_init_script("try{localStorage.setItem('myco-graph-hint','done')}catch(e){}")   # no first-visit hint over the picture
        pg = ctx.new_page()
        pg.goto(url + "?theme=dark")
        pg.wait_for_timeout(1500)
        pg.click("#fold")                                  # the search panel folds: more room for the colony
        pg.select_option("#speed", "2")
        pg.evaluate("window.__turn(0,0)")
        shot = lambda: Image.open(__import__("io").BytesIO(pg.screenshot())).convert("RGB")
        pg.click("#play")
        pg.wait_for_timeout(200)
        for i in range(160):                               # the replay, to its end
            frames.append(shot()); durs.append(90)
            if i > 10 and pg.inner_text("#play") != "Pause":
                break
        for i in range(8):
            frames.append(shot()); durs.append(90)
        for t in THEMES:                                   # turn in 3D while the themes change
            pg.evaluate("(function(t){var s=document.getElementById('theme-pick');s.value=t;s.dispatchEvent(new Event('change'))})('%s')" % t)
            for i in range(16):
                pg.evaluate("window.__turn(.05,.12)")
                frames.append(shot()); durs.append(90)
        gallery = []
        pg.click("#saver")                                 # screensaver: no panels, the network centred
        pg.wait_for_timeout(1500)
        for t in THEMES[:6]:                               # one still per theme for the gallery
            pg.evaluate("(function(t){var s=document.getElementById('theme-pick');s.value=t;s.dispatchEvent(new Event('change'))})('%s')" % t)
            pg.wait_for_timeout(900)
            gallery.append(shot().crop((120, 40, 840, 600)))
        b.close()
    out = os.path.join(HERE, "mycelium.webp")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0, quality=62, method=4)
    W, H = 360, 280
    g = Image.new("RGB", (W * 3 + 8, H * 2 + 4), (13, 17, 23))
    for k, im in enumerate(gallery):
        g.paste(im.resize((W, H)), ((k % 3) * (W + 4), (k // 3) * (H + 4)))
    g.save(os.path.join(HERE, "graph-themes.webp"), quality=80)
    print("wrote", out, os.path.getsize(out) // 1024, "KB;", os.path.join(HERE, "graph-themes.webp"))


if __name__ == "__main__":
    main()
