#!/usr/bin/env python3
"""A self-contained HTML preview of a day's posts: every slide embedded (base64), the caption as it
will appear, sources, checks and rejected candidates. For PREVIEW runs (reference/autopilot.md),
where the run shares this page (for example as a Claude Artifact) instead of posting.

    python3 preview_page.py <day_dir>   -> <day_dir>/preview.html
"""
import base64, html, io, json, pathlib, sys

day = pathlib.Path(sys.argv[1])
spec = json.loads((day / "posts.json").read_text()); man = json.loads((day / "manifest.json").read_text())
rej_f = day / "rejected.json"
rejected = json.loads(rej_f.read_text()) if rej_f.exists() else []
esc = html.escape


def img(n):
    # 720 px wide at q80: a 10-slide carousel stays a few MB
    from PIL import Image
    im = Image.open(day / "jpg" / f"{n[:-5]}.jpg").convert("RGB")
    im = im.resize((720, round(im.height * 720 / im.width)))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=80)
    return f'<img src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="slide">'


def ul(xs):
    return "<ul>" + "".join(f"<li>{esc(str(x))}</li>" for x in xs) + "</ul>" if xs else "<p class=m>-</p>"


cards = []
for p in spec["posts"]:
    k = len(man[p["id"]])
    cards.append(f"""<section class=post><header><span class=tag>{esc(p['series'])}</span>
<span class=m>{esc(p.get('time',''))} · {'single' if k == 1 else f'carousel · {k}'}</span></header>
<div class=strip>{''.join(img(n) for n in man[p['id']])}</div>
<h3>Caption</h3><pre class=cap dir=auto>{esc(p['caption'])}</pre>
<div class=cols><div><h3>Sources</h3>{ul(p.get('sources', []))}</div><div><h3>Checks</h3>{ul(p.get('checks', []))}</div>
<div><h3>Data</h3>{ul(p.get('data', []))}</div></div></section>""")
rej = "".join(f"<tr><td>{esc(r.get('candidate',''))}</td><td>{esc(r.get('reason',''))}</td></tr>" for r in rejected)
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name=viewport content="width=device-width,initial-scale=1">
<title>Instagram preview</title>
<style>
:root{{--ink:#14161A;--paper:#F6F7F9;--line:#DDE1E6;--mute:#5F6670;--accent:#0FA89A;--card:#fff}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--ink:#EEF0F3;--paper:#111315;--line:#2A2E33;--mute:#9AA1AA;--card:#181B1E}}}}
:root[data-theme="dark"]{{--ink:#EEF0F3;--paper:#111315;--line:#2A2E33;--mute:#9AA1AA;--card:#181B1E}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,sans-serif;padding:24px 16px}}
.wrap{{max-width:1100px;margin:0 auto}}h1{{font-size:24px;margin:0 0 4px}}.m{{color:var(--mute);font-size:14px}}
.post{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:18px 0}}
header{{display:flex;gap:12px;align-items:center;margin-bottom:12px}}.tag{{background:var(--accent);color:#fff;border-radius:999px;padding:3px 12px;font-weight:600;font-size:14px}}
.strip{{display:flex;gap:10px;overflow-x:auto;padding-bottom:8px}}.strip img{{width:270px;max-width:80vw;aspect-ratio:4/5;border-radius:10px;border:1px solid var(--line);flex:0 0 auto}}
.cap{{white-space:pre-wrap;font-family:inherit;background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:12px;font-size:14px;line-height:1.55;unicode-bidi:plaintext}}
.cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}}h3{{font-size:15px;margin:14px 0 6px}}ul{{margin:0;padding-inline-start:18px;font-size:13.5px;line-height:1.5}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}td{{border-top:1px solid var(--line);padding:8px;vertical-align:top}}
</style></head><body><div class=wrap><h1>Preview · {esc(spec['date'])}</h1>
<p class=m>What the run would have posted. Not published.</p>{''.join(cards)}
<section class=post><h3>Rejected candidates</h3><table>{rej or '<tr><td class=m>-</td></tr>'}</table></section></div></body></html>"""
(day / "preview.html").write_text(page)
print(day / "preview.html", f"{len(page)//1024} KB")
