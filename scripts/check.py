#!/usr/bin/env python3
"""The copy gate. Run it before review; it must print OK before anything is shown or posted.

    python3 check.py <day_dir>          # exit 1 on any failure

Per post it checks:
- every number in the caption appears on that post's slides or in its "facts" list
  (so a caption cannot quote a figure the validated slides do not carry);
- every post has data, checks and sources filled in;
- the brand's copy rules (brand.json "copy"): no banned word (competitors, vendors, anything
  you never want to name), no banned pattern, no em dash unless "allow_em_dash": true;
- only the news slide types are used;
- the topic_key has not been posted before (ledger.json one level up from the day), and the
  caption's first line does not repeat a recent post (posted.json, written by posted.py).
"""
import html, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import BRAND

COPY = BRAND.get("copy", {})
day = pathlib.Path(sys.argv[1])
spec = json.loads((day / "posts.json").read_text())
ledger_f = day.parent / "ledger.json"
ledger = json.loads(ledger_f.read_text()) if ledger_f.exists() else []
posted_keys = {e.get("topic_key") for e in ledger}
posted_f = day.parent / "posted.json"   # what is actually on the account: the source of truth in a cloud run
posted_hooks = [h["hook"] for h in json.loads(posted_f.read_text())] if posted_f.exists() else []

BANNED = [w for w in COPY.get("banned_words", []) if w]
BANNED_RE = re.compile("|".join(re.escape(w) for w in BANNED), re.I) if BANNED else None
PATTERNS = [(re.compile(p["regex"] if isinstance(p, dict) else p), p.get("why", "") if isinstance(p, dict) else "")
            for p in COPY.get("banned_patterns", [])]
NUM = r"(?<![A-Za-z])\d+(?:[.,]\d+)*"  # "N12", "i24": names, not claims
NEWS_TYPES = {"news", "news_text", "item", "news_end"}


def _w(t):
    return {w for w in re.sub(r"[^\w\s]", " ", t.lower()).split() if len(w) > 2}


def nums(s):
    return {x.replace(",", "") for x in re.findall(NUM, s)}


def text_of(slide):
    t = " ".join(str(v) for k, v in slide.items() if k not in ("type", "art", "insets"))
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


fail = []
for p in spec["posts"]:
    pid = p["id"]
    allowed = set()
    for s in p["slides"]:
        allowed |= nums(text_of(s))
    allowed |= {str(f).replace(",", "") for f in p.get("facts", [])}
    allowed |= {part for a in list(allowed) for part in a.split(".")}   # "24.9–30.9" also licenses "24" and "30"
    claims = re.sub(r"#\S+", "", p["caption"])                          # hashtags are not claims
    for x in sorted(nums(claims) - allowed):
        fail.append(f"{pid}: caption number {x} is not on a slide and not in facts")
    for field in ("data", "checks", "sources"):
        if not p.get(field):
            fail.append(f"{pid}: '{field}' is empty: say where the numbers came from and how they were checked")
    copy = p["caption"] + " " + " ".join(text_of(s) for s in p["slides"])
    if "—" in copy and not COPY.get("allow_em_dash"):
        fail.append(f"{pid}: em dash in copy")
    if BANNED_RE and (m := BANNED_RE.search(copy)):
        fail.append(f"{pid}: banned word in copy: {m.group(0)}")
    for rx, why in PATTERNS:
        if m := rx.search(copy):
            fail.append(f"{pid}: banned pattern {m.group(0)!r}" + (f" ({why})" if why else ""))
    other = [s["type"] for s in p["slides"] if s["type"] not in NEWS_TYPES]
    if other:
        fail.append(f"{pid}: slide types {other} are not part of the look; use {sorted(NEWS_TYPES)}")
    if p.get("topic_key") and p["topic_key"] in posted_keys:
        fail.append(f"{pid}: topic_key {p['topic_key']} was already posted")
    hook = _w(p["caption"].split("\n")[0])
    for h in posted_hooks:
        hw = _w(h)
        if hook and hw and len(hook & hw) / len(hook | hw) >= 0.45:
            fail.append(f"{pid}: repeats a recent post: {h[:70]}"); break

print("\n".join(fail) if fail else f"OK: {len(spec['posts'])} posts pass the copy gate")
sys.exit(1 if fail else 0)
