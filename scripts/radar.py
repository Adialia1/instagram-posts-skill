#!/usr/bin/env python3
"""News radar: which stories in your niche are out there right now, how many outlets carry each
one, and whether you already posted it.

    python3 radar.py [<base_dir>] [--days 7]
      -> <base_dir>/radar/<date>.json and <date>.md

Sources: Google News search RSS for every query in brand.json "radar.queries" (keyed by language:
"en", "he", ...; Google News aggregates most outlets), plus any direct RSS feeds in "radar.feeds"
({"name": "url"}). A headline must match "radar.topic_words" (a regex) to count.

A story is a CLUSTER of headlines that share most of their words. Its score rewards corroboration
(distinct outlets: the validation rule wants two), recency, and angles that travel on Instagram
(a record, a famous name + a price, a surprising %). A story whose words match a post already in
ledger.json is marked "covered". The radar finds candidates; it never replaces reading the article.
"""
import argparse, datetime as dt, email.utils, html, json, pathlib, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import BRAND, home, tz

R = BRAND.get("radar", {})
GN = "https://news.google.com/rss/search?q={q}+when:{d}d&hl={hl}&gl={gl}&ceid={gl}:{hl}"
REGION = {"en": ("en-US", "US"), "he": ("he", "IL"), "fr": ("fr", "FR"), "de": ("de", "DE"), "es": ("es", "ES"),
          "it": ("it", "IT"), "pt": ("pt-BR", "BR"), "ar": ("ar", "AE")}
BOOST = {r"record|most expensive|priciest|שיא|הכי יקר": 3,
         r"billion|מיליארד": 2, r"million|מיליון|\$|€|£|₪": 1,
         r"celebrity|star|billionaire|סלב|מיליארדר": 2,
         r"\d+(\.\d+)?%|soar|plunge|crash|surge|זינוק|צניחה": 2,
         r"penthouse|mansion|villa|estate|פנטהאוז|וילה|אחוזה": 1,
         r"bizarre|viral|weird|squatter|מוזר|ויראלי": 2}
NOISE = r"homes sold in|most expensive homes sold|recent home sales|in .{0,25} county|sponsored|advertorial"
TOPIC = R.get("topic_words") or "."
STOP = set("the a an of to in on for and with at by from is are was be as its it this that new של את על עם זה זו לא כי גם או אם יש".split())
UA = {"User-Agent": "Mozilla/5.0 (compatible; instagram-posts-radar/1.0)"}


def fetch(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
    except Exception:
        return b""


def parse(xml, feed):
    out = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return out
    for it in root.iter("item"):
        title = html.unescape((it.findtext("title") or "").strip())
        src = it.findtext("source") or feed
        if feed.startswith("gn:") and " - " in title:
            title, src = title.rsplit(" - ", 1)
        pub = it.findtext("pubDate")
        try:
            when = email.utils.parsedate_to_datetime(pub).astimezone(dt.timezone.utc) if pub else None
        except Exception:
            when = None
        src = re.sub(r"\.(co\.\w+|com|net|org)$", "", src.strip(), flags=re.I)
        out.append({"title": title.strip(), "source": src, "link": (it.findtext("link") or "").strip(),
                    "published": when.isoformat() if when else None, "feed": feed})
    return out


def words(t):
    t = re.sub(r"[\"'״׳“”‘’()\[\]:,.!?\-–—|]", " ", t.lower())
    return {w for w in t.split() if len(w) > 1 and w not in STOP}


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("base", nargs="?"); ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    base = pathlib.Path(a.base).expanduser() if a.base else home(); (base / "radar").mkdir(parents=True, exist_ok=True)
    urls = {}
    for lang, qs in (R.get("queries") or {}).items():
        hl, gl = REGION.get(lang, (lang, "US"))
        urls |= {f"gn:{lang}:{q}": GN.format(q=urllib.parse.quote(q), d=a.days, hl=hl, gl=gl) for q in qs}
    urls |= R.get("feeds") or {}
    if not urls:
        sys.exit("no radar queries or feeds in brand.json")
    with ThreadPoolExecutor(8) as ex:
        raw = dict(zip(urls, ex.map(fetch, urls.values())))
    now = dt.datetime.now(dt.timezone.utc); cutoff = now - dt.timedelta(days=a.days)
    items, seen = [], set()
    for feed, x in raw.items():
        for it in parse(x, feed):
            key = (it["title"], it["source"])
            if key in seen or not it["title"]: continue
            if it["published"] and dt.datetime.fromisoformat(it["published"]) < cutoff: continue
            seen.add(key); it["w"] = words(it["title"]); items.append(it)
    clusters = []   # greedy: a headline joins the cluster whose words it shares most
    for it in sorted(items, key=lambda i: i["published"] or "", reverse=True):
        best = max(clusters, key=lambda c: jaccard(c["w"], it["w"]), default=None)
        if best and jaccard(best["w"], it["w"]) >= 0.34:
            best["items"].append(it); best["w"] |= it["w"]
        else:
            clusters.append({"w": set(it["w"]), "items": [it]})
    ledger_f = base / "ledger.json"
    posted = json.loads(ledger_f.read_text()) if ledger_f.exists() else []
    posted_w = [words((e.get("title") or "") + " " + (e.get("topic_key") or "").replace("-", " ").replace(":", " ")) for e in posted]
    home_lang = BRAND.get("lang", "en")
    stories = []
    for c in clusters:
        its = c["items"]; outlets = sorted({i["source"] for i in its})
        newest = max((i["published"] for i in its if i["published"]), default=None)
        age_d = (now - dt.datetime.fromisoformat(newest)).total_seconds() / 86400 if newest else a.days
        head = max(its, key=lambda i: len(i["title"]))["title"]
        text = " ".join(i["title"] for i in its)
        lang = its[0]["feed"].split(":")[1] if its[0]["feed"].startswith("gn:") else home_lang
        boost = sum(v for pat, v in BOOST.items() if re.search(pat, text, re.I))
        covered = max((jaccard(words(head), w) for w in posted_w), default=0) >= 0.3
        noise = bool(re.search(NOISE, text, re.I)) or not re.search(TOPIC, text, re.I)
        score = round(3 * min(len(outlets), 4) + max(0, 3 - age_d) + boost + (2 if lang == home_lang else 0)
                      - (10 if covered else 0) - (8 if noise else 0), 1)
        stories.append({"score": score, "outlets": outlets, "n_outlets": len(outlets), "newest": newest,
                        "headline": head, "covered": covered, "lang": lang,
                        "items": [{k: i[k] for k in ("title", "source", "link", "published")} for i in its]})
    stories.sort(key=lambda s: -s["score"])
    day = now.astimezone(tz()).date().isoformat()
    (base / "radar" / f"{day}.json").write_text(json.dumps(stories, ensure_ascii=False, indent=1))
    lines = [f"# Radar {day} · {len(items)} headlines · {len(stories)} stories · last {a.days} days"]
    for lang in sorted({s["lang"] for s in stories}):
        lines += ["", f"## {lang}", "", "| score | outlets | newest | story | covered |", "|---|---|---|---|---|"]
        for s in [x for x in stories if x["lang"] == lang][:20]:
            lines.append(f'| {s["score"]} | {s["n_outlets"]}: {", ".join(s["outlets"][:4])} | {(s["newest"] or "")[:10]} | {s["headline"][:110].replace("|", "/")} | {"✓" if s["covered"] else ""} |')
    (base / "radar" / f"{day}.md").write_text("\n".join(lines))
    print(f"{len(items)} headlines, {len(stories)} stories -> {base}/radar/{day}.md")
    print("\n".join(lines[1:18]))


if __name__ == "__main__":
    main()
