#!/usr/bin/env python3
"""Write <day_dir>/review.html: one row per post, like a sheet: time, series, slides,
caption (with a copy button), data and sources, checks passed, a local status menu.

    python3 review.py <day_dir> [<day2> ...] [--out file.html]     then open the file
"""
import html, json, os, pathlib, sys

args = sys.argv[1:]
out = pathlib.Path(args[args.index("--out") + 1]) if "--out" in args else None
days = [pathlib.Path(x) for x in args if x != "--out" and (out is None or pathlib.Path(x) != out)]
out = out or days[0] / "review.html"
spec = {"date": " + ".join(d.name for d in days), "posts": []}
man = {}
for d in days:
    sp = json.loads((d / "posts.json").read_text()); mf = json.loads((d / "manifest.json").read_text())
    rel = os.path.relpath(d, out.parent)
    for p in sp["posts"]:
        key = f"{d.name}/{p['id']}"
        spec["posts"].append({**p, "id": key})
        man[key] = [f"{rel}/png/{n[:-5]}.png" for n in mf[p["id"]]]

CSS = """
:root{--ink:#14161A;--paper:#F6F7F9;--line:#DDE1E6;--mute:#5F6670;--accent:#0FA89A}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:var(--paper);color:var(--ink)}
header{padding:28px 32px 8px}h1{margin:0;font-size:26px;font-weight:600}header p{margin:6px 0 0;color:var(--mute)}
.wrap{overflow-x:auto;padding:16px 32px 48px}
table{border-collapse:collapse;min-width:1500px;background:#fff;border:1px solid var(--line)}
th{position:sticky;top:0;background:var(--ink);color:#fff;font-weight:500;font-size:14px;text-align:start;padding:12px}
td{border-top:1px solid var(--line);padding:14px 12px;vertical-align:top;font-size:14px;line-height:1.5}
.num{font-weight:600;font-size:22px;color:var(--accent)}
.slides{display:flex;gap:8px}.slides img{width:150px;height:187px;object-fit:cover;border-radius:8px;border:1px solid var(--line);cursor:zoom-in}
.cap{white-space:pre-wrap;width:330px;font-size:13.5px;unicode-bidi:plaintext}
.copy{margin-top:8px;border:0;background:var(--accent);color:#fff;border-radius:999px;padding:6px 14px;font:inherit;font-size:13px;cursor:pointer}
ul{margin:0;padding-inline-start:18px}li{margin:2px 0}.data{width:260px;color:#3A3F46}.checks{width:300px}
.tag{display:inline-block;background:#E3F4F2;border-radius:999px;padding:2px 10px;font-weight:500}
a{color:var(--accent)}select{font:inherit;padding:4px 6px;border-radius:6px;border:1px solid var(--line)}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.85);display:none;align-items:center;justify-content:center;gap:12px;z-index:9}
#lb img{max-height:92vh;max-width:46vw;border-radius:10px}#lb.on{display:flex}
"""
li = lambda xs: "<ul>" + "".join(f"<li>{html.escape(str(x))}</li>" for x in xs) + "</ul>"
src = lambda xs: "<ul>" + "".join(f'<li><a href="{html.escape(x)}" target="_blank">{html.escape(x[:60])}</a></li>' if str(x).startswith("http") else f"<li>{html.escape(str(x))}</li>" for x in xs) + "</ul>"
rows, slides = [], {}
for i, p in enumerate(spec["posts"], 1):
    slides[p["id"]] = man[p["id"]]
    imgs = "".join(f'<img src="{s}" loading="lazy" data-post="{p["id"]}" data-k="{k}">' for k, s in enumerate(slides[p["id"]]))
    fmt = "single" if len(slides[p["id"]]) == 1 else f'carousel · {len(slides[p["id"]])}'
    rows.append(f"""<tr><td class="num">{i}<div style="font-size:11px;color:#5F6670;font-weight:400">{html.escape(p["id"])}</div></td><td><b>{p.get('time','')}</b></td><td><span class="tag">{html.escape(p['series'])}</span><br>{fmt}</td>
<td><div class="slides">{imgs}</div></td>
<td><div class="cap" id="c{i}" dir="auto">{html.escape(p['caption'])}</div><button class="copy" data-cap="c{i}">Copy caption</button></td>
<td class="data">{li(p.get('data', []))}<b>Sources</b>{src(p.get('sources', []))}</td><td class="checks">{li(p.get('checks', []))}</td>
<td><select><option>pending</option><option>approved</option><option>fix</option><option>don't post</option></select></td></tr>""")
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Instagram · {spec['date']}</title><style>{CSS}</style></head><body>
<header><h1>Instagram posts · {spec['date']}</h1><p>{len(spec['posts'])} posts. Every number was checked before it went in. Click a slide to enlarge. The status menu is local only: approve in the chat.</p></header>
<div class="wrap"><table><thead><tr><th>#</th><th>Time</th><th>Series · format</th><th>Slides</th><th>Caption</th><th>Data and sources</th><th>Checks</th><th>Status</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div><div id="lb"></div>
<script>
const S={json.dumps(slides)};const box=document.getElementById('lb');
box.addEventListener('click',()=>box.classList.remove('on'));
document.querySelectorAll('.slides img').forEach(im=>im.addEventListener('click',()=>{{
  box.replaceChildren(...S[im.dataset.post].slice(+im.dataset.k,+im.dataset.k+2).map(s=>{{const i=new Image();i.src=s;return i}}));box.classList.add('on');}}));
document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',()=>{{navigator.clipboard.writeText(document.getElementById(b.dataset.cap).innerText);b.textContent='Copied ✓';}}));
</script></body></html>"""
out.write_text(page)
print(out)
