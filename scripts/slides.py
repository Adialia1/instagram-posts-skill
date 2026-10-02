#!/usr/bin/env python3
"""Turn a day's posts.json into 1080x1350 HTML slides in the news look.

    python3 slides.py <day_dir>      # reads <day_dir>/posts.json, writes <day_dir>/slides/*.html + manifest.json

The look: a vivid photo on top, one or two round insets with an accent ring, the brand
wordmark on a thin divider line, then a black band with a heavy condensed headline whose
key words are in the accent colour, and one small credit line. Every post looks the same
on purpose, so the page reads as a news brand. Colours, fonts, the logo and the wordmark
come from brand.json; "lang": "he" (or another RTL language) flips the whole layout.

Every word and number is typeset here. The art (art/<name>.jpg, made by art.py) never
contains text: image models redraw letters and digits wrong, Hebrew worst of all.

Slide types (reference/posts-schema.md has every field):
  news       a single-image post, or a carousel's cover
  news_text  a carousel's inner slide: photo strip, title, paragraph
  item       one thing per slide with a rank badge and a big value (top-N lists)
  news_end   the last slide: logo, follow line, call to action
"""
import html, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import BRAND, skill_path, rtl

C, F, COPY = BRAND["colors"], BRAND["fonts"], BRAND["copy"]
RTL = rtl()
DIR = "rtl" if RTL else "ltr"
START, END = ("right", "left") if RTL else ("left", "right")   # the reading start side

CSS = f"""
@import url('{skill_path(F["css"]).as_uri()}');
:root{{--accent:{C["accent"]};--bg:{C["background"]};--ink:{C["text"]};--muted:{C["muted"]}}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1080px;height:1350px;overflow:hidden}}
body{{font-family:'{F["body"]}',sans-serif;direction:{DIR};color:var(--ink);background:var(--bg);position:relative;font-weight:400}}
.n{{direction:ltr;unicode-bidi:isolate;display:inline-block}}
.o{{color:var(--accent)}}
.photo{{position:absolute;top:0;left:0;width:1080px;object-fit:cover}}
.fade{{position:absolute;left:0;width:1080px;background:linear-gradient(to bottom,rgba(0,0,0,0),var(--bg))}}
.progress{{position:absolute;top:22px;left:36px;right:36px;display:flex;gap:8px;z-index:5;direction:{DIR}}}
.progress i{{flex:1;height:6px;border-radius:3px;background:rgba(255,255,255,.35);box-shadow:0 1px 4px rgba(0,0,0,.4)}}
.progress i.on{{background:var(--accent)}}
.inset{{position:absolute;border-radius:50%;overflow:hidden;border:7px solid var(--accent);outline:5px solid var(--bg);box-shadow:0 16px 36px rgba(0,0,0,.5);z-index:3;background:#fff}}
.inset img,.inset svg{{width:100%;height:100%;object-fit:cover;display:block}}
.credit{{position:absolute;{START}:40px;max-width:70%;font-size:17px;line-height:1.35;color:rgba(255,255,255,.8);z-index:4;text-shadow:0 1px 3px rgba(0,0,0,.9);text-align:{START}}}
.divider{{position:absolute;left:48px;right:48px;display:flex;align-items:center;gap:20px;z-index:4}}
.divider i{{flex:1;height:2px;background:var(--accent)}}
.wm{{display:inline-flex;align-items:center;gap:14px;white-space:nowrap;line-height:1;font-size:38px;font-weight:400;letter-spacing:.2px}}
.wm b{{font-weight:800}}
.logo{{width:56px;height:56px;flex:0 0 56px;display:block}}
.logo svg,.logo img{{width:100%;height:100%;display:block}}
.hl{{position:absolute;left:44px;right:44px;text-align:center;font-family:'{F["headline"]}',sans-serif;font-weight:{F.get("headline_weight", 800)};font-stretch:{F.get("headline_stretch", "100%")};line-height:.98;letter-spacing:0;z-index:4}}
.body{{position:absolute;left:64px;right:64px;font-size:46px;line-height:1.45;color:var(--muted);z-index:4;text-align:{START}}}
.body b{{color:var(--accent);font-weight:700}}
.foot{{position:absolute;bottom:20px;left:0;right:0;text-align:center;font-size:18px;color:rgba(255,255,255,.5);direction:ltr;z-index:4;letter-spacing:.5px}}
.rank{{position:absolute;top:58px;{START}:44px;min-width:150px;height:150px;padding:0 22px;border-radius:30px;background:var(--accent);color:var(--bg);display:flex;align-items:center;justify-content:center;font-family:'{F["headline"]}',sans-serif;font-weight:{F.get("headline_weight", 800)};font-stretch:{F.get("headline_stretch", "100%")};font-size:120px;line-height:1;z-index:4;direction:ltr;box-shadow:0 14px 30px rgba(0,0,0,.45)}}
.pill{{display:inline-flex;align-items:center;gap:14px;border-radius:999px;padding:16px 34px;font-size:30px;font-weight:700;background:var(--accent);color:var(--bg)}}
"""

FLAGS = {
    "il": '<svg viewBox="0 0 220 160" preserveAspectRatio="xMidYMid slice"><rect width="220" height="160" fill="#fff"/><rect y="18" width="220" height="22" fill="#0038b8"/><rect y="120" width="220" height="22" fill="#0038b8"/><g fill="none" stroke="#0038b8" stroke-width="6"><path d="M110 52 L136 97 L84 97 Z"/><path d="M110 112 L84 67 L136 67 Z"/></g></svg>',
    "us": '<svg viewBox="0 0 190 100" preserveAspectRatio="xMidYMid slice"><rect width="190" height="100" fill="#fff"/>' + "".join(f'<rect y="{y*100/13:.2f}" width="190" height="{100/13:.2f}" fill="#b22234"/>' for y in range(0, 13, 2)) + '<rect width="76" height="54" fill="#3c3b6e"/></svg>',
    "uk": '<svg viewBox="0 0 60 30" preserveAspectRatio="xMidYMid slice"><rect width="60" height="30" fill="#012169"/><path d="M0 0L60 30M60 0L0 30" stroke="#fff" stroke-width="6"/><path d="M0 0L60 30M60 0L0 30" stroke="#C8102E" stroke-width="2"/><path d="M30 0V30M0 15H60" stroke="#fff" stroke-width="10"/><path d="M30 0V30M0 15H60" stroke="#C8102E" stroke-width="6"/></svg>',
    "fr": '<svg viewBox="0 0 3 2" preserveAspectRatio="xMidYMid slice"><rect width="1" height="2" fill="#0055A4"/><rect x="1" width="1" height="2" fill="#fff"/><rect x="2" width="1" height="2" fill="#EF4135"/></svg>',
    "de": '<svg viewBox="0 0 5 3" preserveAspectRatio="xMidYMid slice"><rect width="5" height="1" fill="#000"/><rect y="1" width="5" height="1" fill="#DD0000"/><rect y="2" width="5" height="1" fill="#FFCE00"/></svg>',
    "jp": '<svg viewBox="0 0 3 2" preserveAspectRatio="xMidYMid slice"><rect width="3" height="2" fill="#fff"/><circle cx="1.5" cy="1" r=".6" fill="#BC002D"/></svg>',
}
# Inset spots are named by reading side, so an RTL page mirrors them: "s" = start, "e" = end.
SPOTS = {"te": f"top:86px;{END}:44px", "ts": f"top:120px;{START}:44px",
         "me": f"top:380px;{END}:36px", "ms": f"top:380px;{START}:36px"}
SPOTS |= {"tr": SPOTS["ts" if RTL else "te"], "tl": SPOTS["te" if RTL else "ts"],   # old names still work
          "mr": SPOTS["ms" if RTL else "me"], "ml": SPOTS["me" if RTL else "ms"]}


def logo_html():
    p = skill_path(BRAND.get("logo") or "assets/logo.svg")
    if not p.exists():
        return ""
    inner = p.read_text() if p.suffix == ".svg" else f'<img src="{p.as_uri()}">'
    return f'<span class="logo">{inner}</span>'


LOGO = logo_html()
WORDMARK = f'{html.escape(BRAND["name"])} <b>{html.escape(BRAND.get("name_bold", ""))}</b>'.strip()
FOOT = " · ".join(x for x in (BRAND.get("handle"), BRAND.get("site")) if x)

DAY = None  # set by build(): person insets read art/<slug>.credit.json from the day folder


def N(x):
    """An LTR-isolated number inside RTL text, so 2.6% and 24.9–30.9 never flip."""
    return f'<span class="n">{x}</span>'


def page(body):
    return (f'<!doctype html><html lang="{BRAND.get("lang", "en")}" dir="{DIR}"><head><meta charset="utf-8">'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


def progress(i, n):
    if n < 2:
        return ""
    return '<div class="progress">' + "".join(f'<i class="{"on" if k == i else ""}"></i>' for k in range(1, n + 1)) + "</div>"


def insets(s):
    out = []
    for x in s.get("insets", []):
        size = x.get("size", 260)
        inner = FLAGS[x["flag"]] if "flag" in x else f'<img src="../art/{x.get("person") or x["art"]}.jpg">'
        out.append(f'<div class="inset" style="{SPOTS[x.get("at", "te")]};width:{size}px;height:{size}px">{inner}</div>')
    return "".join(out)


def credit_line(s, h):
    """The slide's credit: the picture's, then every person inset's (a real photo from
    person.py carries its photographer and licence). One credit per line, each isolated,
    so Hebrew and Latin never reorder each other."""
    parts = [s.get("credit", COPY.get("credit_default", "Media: AI · illustrative image"))]
    for x in s.get("insets", []):
        if x.get("person"):
            c = json.loads((DAY / "art" / f'{x["person"]}.credit.json').read_text())
            if c["credit"] not in parts:
                parts.append(c["credit"])
    lines = "".join(f'<div dir="auto">{p}</div>' for p in parts)
    return f'<div class="credit" style="top:{h - 40}px;transform:translateY(-100%)">{lines}</div>'


def photo(s, h, fade=180):
    return (f'<img class="photo" style="height:{h}px" src="../art/{s["art"]}.jpg">'
            f'<div class="fade" style="top:{h - fade}px;height:{fade}px"></div>')


def divider(y):
    return f'<div class="divider" style="top:{y}px"><i></i><span class="wm">{LOGO}<span>{WORDMARK}</span></span><i></i></div>'


def foot():
    return f'<div class="foot">{FOOT}</div>' if FOOT else ""


def news(s, i, n):
    """A single-image post or a carousel's cover."""
    h = s.get("photo_h", 860)
    return page(f'''{photo(s, h)}{credit_line(s, h)}{progress(i, n)}{insets(s)}{divider(h - 8)}
<div class="hl" style="top:{h + 70}px;font-size:{s.get("size", 104)}px">{s["headline"]}</div>{foot()}''')


def news_text(s, i, n):
    """A carousel's inner slide: a photo strip, a condensed title, a paragraph (≤ ~45 words)."""
    h = s.get("photo_h", 720)
    size = s.get("size", 96)
    body_top = h + 70 + int(size * 1.0 * s.get("title_lines", 1)) + 36
    return page(f'''{photo(s, h, 140)}{credit_line(s, h)}{progress(i, n)}{insets(s)}{divider(h - 8)}
<div class="hl" style="top:{h + 70}px;font-size:{size}px">{s["title"]}</div>
<div class="body" style="top:{body_top}px">{s["body"]}</div>{foot()}''')


def item(s, i, n):
    """One thing per slide, with its picture: the image-led top-N."""
    h = s.get("photo_h", 820)
    return page(f'''{photo(s, h)}{credit_line(s, h)}{progress(i, n)}
<div class="rank">{s["rank"]}</div>{divider(h - 8)}
<div class="hl" style="top:{h + 66}px;font-size:{s.get("size", 88)}px">{s["title"]}</div>
<div class="body" style="top:{h + 166}px;text-align:center;font-size:30px">{s.get("detail", "")}</div>
<div class="hl" style="top:{h + 248}px;font-size:{s.get("value_size", 124)}px"><span class="o">{N(s["value"])}</span> {s.get("unit", "")}</div>{foot()}''')


def news_end(s, i, n):
    """The last slide of a carousel: follow us. Never a face here (it would read as an endorsement)."""
    big_logo = LOGO.replace('class="logo"', 'class="logo" style="width:180px;height:180px;flex:0 0 180px"')
    follow = html.escape(COPY.get("end_follow", "Follow us"))
    return page(f'''{progress(i, n)}<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:36px">
{big_logo}
<div class="hl" style="position:static;font-size:{s.get("size", 120)}px">{s.get("headline", COPY.get("end_headline", ""))}</div>
<div style="font-size:34px;color:var(--muted)">{follow} <span class="n">{html.escape(BRAND.get("handle", ""))}</span></div>
<span class="pill">{s.get("cta", COPY.get("end_cta", ""))}</span></div>{foot()}''')


KINDS = {"news": news, "news_text": news_text, "item": item, "news_end": news_end}

RANGE = re.compile(r'(?<!class="n">)(?<![\w.])(\d+(?:\.\d+)?–\d+(?:\.\d+)?)')


def isolate_ranges(s):
    """24.9–30.9 and 1–5 always read left to right. Left to the bidi algorithm, an en dash
    between two numbers in RTL text flips the range on some slides and not on others."""
    out = {}
    for k, v in s.items():
        if isinstance(v, str) and k not in ("type", "art"):
            v = RANGE.sub(r'<span class="n">\1</span>', v)
        out[k] = v
    return out


def build(day):
    global DAY
    day = DAY = pathlib.Path(day)
    spec = json.loads((day / "posts.json").read_text())
    out = day / "slides"
    out.mkdir(exist_ok=True)
    manifest = {}
    for p in spec["posts"]:
        slides = [isolate_ranges(s) for s in p["slides"]]
        n = len(slides)
        names = []
        for i, s in enumerate(slides, 1):
            if s["type"] not in KINDS:
                sys.exit(f'{p["id"]} slide {i}: unknown type {s["type"]!r}; use one of {sorted(KINDS)}')
            name = f'{p["id"]}_{i}.html'
            (out / name).write_text(KINDS[s["type"]](s, i, n))
            names.append(name)
        manifest[p["id"]] = names
    (day / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1]), ensure_ascii=False))
