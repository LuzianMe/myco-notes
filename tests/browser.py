#!/usr/bin/env python3
"""Browser test of the mycelium view (graph.html): the page opened with no size, and embed mode. Needs Playwright for Python with
Chromium (pip install playwright && python -m playwright install chromium); the kit itself does not. Without Playwright it says so
and exits 0, so the other tests stay dependency-free; CI installs it and runs this on Linux.

    python3 tests/browser.py [--chromium PATH]

It builds the demo notes, their full map and a public graph with a small labels file, serves them locally, and checks in host pages:
  - a graph opened in a hidden (0x0) iframe draws once the iframe is shown, with no error;
  - embed mode (?embed=1, and every public graph) in deepsea and amber: no console error, only the canvas, a transparent page,
    {type:"myco-ready"} sent, the device pixel ratio capped at 1.5, the tilt locked;
  - ?interactive=0 takes no pointer input; the host's messages switch the theme and pause and resume the drawing, and the same
    messages from anyone but the parent are ignored.
Exit 0 = all passed (or Playwright missing), 1 = a check failed.
"""
import argparse
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

sys.dont_write_bytecode = True
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


HOST = """<!doctype html><html><head><meta charset="utf-8"><title>host</title></head>
<body style="margin:0;background:rgb(200,30,120)"><iframe id="f" style="%s;width:640px;height:420px;border:0" src="%s"></iframe>
<script>window.got=[];addEventListener("message",function(e){if(e.source===document.getElementById("f").contentWindow)got.push(e.data)})</script></body></html>"""
COUNT_FRAMES = ("(function(){var r=window.requestAnimationFrame.bind(window);window.__frames=0;"
                "window.requestAnimationFrame=function(f){window.__frames++;return r(f)}})()")
CENTROID = ("(function(){var c=document.getElementById('c'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data,sx=0,sy=0,k=0;"
            "for(var y=0;y<c.height;y+=2)for(var x=0;x<c.width;x+=2)if(d[(y*c.width+x)*4+3]>40){sx+=x;sy+=y;k++}return [sx/k/c.width,sy/k/c.height]})()")
PAINTED = ("(function(){var c=document.getElementById('c'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data,k=0;"
           "for(var i=3;i<d.length;i+=4)if(d[i])k++;return k})()")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chromium", default=None, help="a Chromium or headless-shell binary, if Playwright's own is not installed")
    a = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: Playwright for Python is not installed (pip install playwright && python -m playwright install chromium)")
        return 0
    tmp = tempfile.mkdtemp(prefix="myco-browser-")
    try:
        demo = os.path.join(tmp, "demo")
        subprocess.run([sys.executable, os.path.join(REPO, "examples", "demo", "build_demo.py"), demo], check=True, capture_output=True)
        site = os.path.join(tmp, "site")
        shutil.copytree(os.path.join(demo, "myco-notes", "map"), os.path.join(site, "map"))
        labels = os.path.join(tmp, "labels.json")
        with open(labels, "w", encoding="utf-8") as fh:
            json.dump({"sensor-node": "Sensor node", "gateway": "Gateway"}, fh)
        subprocess.run([sys.executable, os.path.join(demo, "myco-notes", "tools", "build-notes-map.py"), "--root", demo, "--public",
                        "--labels", labels, "--out", os.path.join(site, "pub")], check=True, capture_output=True)

        def host(name, src, style="display:block"):
            with open(os.path.join(site, name), "w", encoding="utf-8") as fh:
                fh.write(HOST % (style, src))

        host("hidden.html", "map/graph.html?theme=deepsea", "display:none")
        for th in ("deepsea", "amber"):
            host(f"embed-{th}.html", f"map/graph.html?embed=1&theme={th}")
            host(f"public-{th}.html", f"pub/graph.html?theme={th}")
        host("still.html", "pub/graph.html?theme=deepsea&interactive=0")
        h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=site)
        h.log_message = lambda *x: None
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_address[1]}/"
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=a.chromium) if a.chromium else p.chromium.launch()
            ctx = b.new_context(viewport={"width": 800, "height": 600}, device_scale_factor=2)
            ctx.add_init_script(COUNT_FRAMES)

            def open_host(name):
                errs = []
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:160]))
                pg.on("console", lambda m: errs.append("console: " + m.text[:160]) if m.type == "error" else None)
                pg.goto(base + name)
                pg.wait_for_timeout(1800)
                return pg, pg.frames[1], errs

            print("a graph opened with no size draws once it gets one")
            pg, fr, errs = open_host("hidden.html")
            size = fr.evaluate("[innerWidth,innerHeight]")
            check("hidden iframe: the page has no size, no error, and no ready message yet", size == [0, 0] and not errs and pg.evaluate("got.length") == 0,
                  f"{size} {errs} {pg.evaluate('got')}")
            pg.evaluate("document.getElementById('f').style.display='block'")
            pg.wait_for_timeout(1500)
            check("shown: it draws, with no error, and says it is ready", fr.evaluate(PAINTED) > 1000 and not errs
                  and pg.evaluate("got").count({"type": "myco-ready"}) == 1, f"{fr.evaluate(PAINTED)} {errs} {pg.evaluate('got')}")
            pg.close()

            for kind in ("embed", "public"):
                for th in ("deepsea", "amber"):
                    print(f"{kind} mode, {th}")
                    pg, fr, errs = open_host(f"{kind}-{th}.html")
                    check(f"{kind} {th}: no console error, and the ready message", not errs and {"type": "myco-ready"} in pg.evaluate("got"),
                          f"{errs} {pg.evaluate('got')}")
                    st = fr.evaluate("""(function(){var v=function(id){var e=document.getElementById(id);return e?getComputedStyle(e).display:'none'};
                        return {ui:['left','tools','panel','hint','time'].map(v),theme:document.documentElement.getAttribute('data-theme'),
                        bg:[getComputedStyle(document.documentElement).backgroundColor,getComputedStyle(document.body).backgroundColor,getComputedStyle(document.body).backgroundImage],
                        cs:getComputedStyle(document.documentElement).colorScheme,mask:getComputedStyle(document.getElementById('c')).maskImage||getComputedStyle(document.getElementById('c')).webkitMaskImage,cw:document.getElementById('c').width,iw:innerWidth}})()""")
                    check(f"{kind} {th}: only the canvas, the theme from ?theme=", st["ui"] == ["none"] * 5 and st["theme"] == th, str(st))
                    check(f"{kind} {th}: a transparent page (color-scheme normal)", st["bg"][:2] == ["rgba(0, 0, 0, 0)"] * 2 and st["bg"][2] == "none"
                          and st["cs"] == "normal", str(st))
                    check(f"{kind} {th}: at most 1.5 device pixels per pixel", st["cw"] == round(st["iw"] * 1.5), str(st))
                    check(f"{kind} {th}: the network is drawn", fr.evaluate(PAINTED) > 1000, "")
                    check(f"{kind} {th}: the edges fade out (a radial mask on the canvas)", "radial-gradient" in (st["mask"] or ""), str(st["mask"]))
                    if kind == "public" and th == "deepsea":
                        box = pg.locator("#f").bounding_box()
                        pg.mouse.move(box["x"] + 40, box["y"] + 40)
                        for k in range(6):
                            pg.mouse.wheel(0, -200)
                            pg.wait_for_timeout(60)
                        pg.wait_for_timeout(1500)
                        c = fr.evaluate(CENTROID)
                        check("zoom: scrolling in near a corner keeps the network in the middle", abs(c[0] - .5) < .08 and abs(c[1] - .5) < .08, str(c))
                        pg.mouse.dblclick(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                        pg.wait_for_timeout(1500)
                        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                        pg.mouse.move(cx, cy)
                        pg.mouse.down()
                        for k in range(1, 16):
                            pg.mouse.move(cx + k * 6, cy - k * 12)
                        pg.mouse.up()
                        pg.wait_for_timeout(300)
                        check("public: a drag turns the view and opens nothing", not errs and fr.evaluate("getComputedStyle(document.getElementById('panel')).display") == "none", str(errs))
                        pg.evaluate("document.getElementById('f').contentWindow.postMessage({type:'myco-theme',theme:'amber'},'*')")
                        pg.wait_for_timeout(300)
                        check("message: the parent switches the theme live", fr.evaluate("document.documentElement.getAttribute('data-theme')") == "amber", "")
                        fr.evaluate("window.postMessage({type:'myco-theme',theme:'paper'},'*')")
                        pg.wait_for_timeout(300)
                        check("message: the same message from anyone but the parent is ignored",
                              fr.evaluate("document.documentElement.getAttribute('data-theme')") == "amber", "")
                        pg.evaluate("document.getElementById('f').contentWindow.postMessage({type:'myco-pause'},'*')")
                        pg.wait_for_timeout(300)
                        n0 = fr.evaluate("window.__frames")
                        pg.wait_for_timeout(700)
                        n1 = fr.evaluate("window.__frames")
                        pg.evaluate("document.getElementById('f').contentWindow.postMessage({type:'myco-resume'},'*')")
                        pg.wait_for_timeout(700)
                        n2 = fr.evaluate("window.__frames")
                        check("message: myco-pause stops the drawing, myco-resume starts it again", n1 == n0 and n2 > n1 + 10, f"{n0} {n1} {n2}")
                        check("messages: no error after all of them", not errs, str(errs))
                    pg.close()

            print("interactive=0")
            pg, fr, errs = open_host("still.html")
            st = fr.evaluate("(function(){var c=getComputedStyle(document.getElementById('c'));return [c.pointerEvents,c.touchAction]})()")
            check("interactive=0: no error, and the canvas takes no pointer or touch", not errs and st[0] == "none" and st[1] == "auto", f"{st} {errs}")
            pg.close()
            b.close()
        srv.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\npassed {passed}, failed {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
