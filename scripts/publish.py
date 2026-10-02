#!/usr/bin/env python3
"""Publish a day's posts to Instagram through Composio, then record them in the ledger.

    python3 publish.py <day_dir> --dry-run --only p1    # host images + build containers, do NOT publish
    python3 publish.py <day_dir> --yes --only p1,p3     # publish some posts
    python3 publish.py <day_dir> --yes                  # every post in posts.json

Refuses without --yes or --dry-run. A post is public the moment it is published, and the
Instagram API can neither edit a caption nor delete a post.

How it works:
- Images must be JPEGs at a public URL. They are uploaded to kie.ai's file host (the same key
  that makes the art; files are deleted after 24 h, long enough for Instagram to fetch them).
- Single: one container with image_url + caption. Carousel: one container per slide
  (is_carousel_item), wait until FINISHED, then a CAROUSEL container with children + caption.
  Then media_publish, then read the post back.
- Limits: Instagram answers "action is blocked" (code 4 / subcode 2207051) to bursts, and may
  publish the post anyway. So: a daily cap counted on Instagram itself, a gap between posts,
  and a went-live check before an error is called a failure. Never retry into a block.
"""
import argparse, datetime as dt, json, pathlib, re, sys, tempfile, time, uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import BRAND, ig_user_id, tz
from composio_connect import ig_call
import kie_image

PUB = BRAND.get("publish", {})
ap = argparse.ArgumentParser(); ap.add_argument("day")
ap.add_argument("--yes", action="store_true"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--only")
ap.add_argument("--max-per-day", type=int, default=PUB.get("max_per_day", 9))
ap.add_argument("--gap", type=int, default=PUB.get("gap_seconds", 600), help="seconds between posts in one run")
ap.add_argument("--ledger", help="ledger.json path (default: next to the day folder)")
a = ap.parse_args()
if not (a.yes or a.dry_run):
    sys.exit("refusing: pass --yes (publish) or --dry-run (containers only)")
UID = ig_user_id()
day = pathlib.Path(a.day).resolve()
spec = json.loads((day / "posts.json").read_text()); man = json.loads((day / "manifest.json").read_text())
posts = [p for p in spec["posts"] if not a.only or p["id"] in a.only.split(",")]
if not posts:
    sys.exit("no posts selected")
tmp = pathlib.Path(tempfile.mkdtemp())


def wait(cid):
    for _ in range(80):
        st = ig_call("GET", f"{cid}?fields=status_code")["status_code"]
        if st == "FINISHED": return
        if st in ("ERROR", "EXPIRED"): raise SystemExit(f"container {cid}: {st}")
        time.sleep(3)
    raise SystemExit(f"container {cid}: timed out")


def recent(n=25):
    return ig_call("GET", f"{UID}/media?fields=id,caption,permalink,timestamp,children{{id}}&limit={n}").get("data", [])


def went_live(caption):
    """After an error on media_publish Instagram may still have published: find it before failing."""
    return next((m for m in recent(5) if (m.get("caption") or "").strip() == caption.strip()), None)


# Daily cap, counted on Instagram itself in the brand's timezone: a ledger may not exist in a cloud run.
zone = tz()
today = dt.datetime.now(zone).date()
posted_today = sum(1 for m in recent(25) if dt.datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(zone).date() == today)
if not a.dry_run and posted_today + len(posts) > a.max_per_day:
    sys.exit(f"refusing: {posted_today} already posted today + {len(posts)} > cap {a.max_per_day}")

key = kie_image.api_key()
ledger_f = pathlib.Path(a.ledger) if a.ledger else day.parent / "ledger.json"
ledger = json.loads(ledger_f.read_text()) if ledger_f.exists() else []
run = uuid.uuid4().hex[:8]
for p in posts:
    # kie.ai stores uploads by file name: make each name unique to this run so runs never overwrite
    urls = []
    for n in man[p["id"]]:
        dst = tmp / f"ig-{day.name}-{run}-{n[:-5]}.jpg"; dst.write_bytes((day / "jpg" / f"{n[:-5]}.jpg").read_bytes())
        urls.append(kie_image.upload(dst, key))
    if len(urls) == 1:
        cid = ig_call("POST", f"{UID}/media", {"image_url": urls[0], "caption": p["caption"]})["id"]
    else:
        kids = [ig_call("POST", f"{UID}/media", {"image_url": u, "is_carousel_item": True})["id"] for u in urls]
        for k in kids: wait(k)
        cid = ig_call("POST", f"{UID}/media", {"media_type": "CAROUSEL", "children": kids, "caption": p["caption"]})["id"]
    wait(cid)
    if a.dry_run:
        print(json.dumps({"id": p["id"], "dry_run": True, "container": cid, "slides": len(urls), "status": "FINISHED",
                          "note": "not published; the container expires on its own"})); continue
    try:
        mid = ig_call("POST", f"{UID}/media_publish", {"creation_id": cid})["id"]
        m = ig_call("GET", f"{mid}?fields=permalink,caption,timestamp,children{{id}}")
    except SystemExit as err:
        time.sleep(20)
        m = went_live(p["caption"])
        if not m:
            raise SystemExit(f"{p['id']}: {err}: NOT live. Stop; do not retry (a retry deepens a block).")
        mid = m["id"]; print(f"{p['id']}: publish answered an error but the post IS live", file=sys.stderr)
    slides = len(m.get("children", {}).get("data", [])) or 1
    first = p["slides"][0]
    rec = {"date": spec["date"], "id": p["id"], "series": p["series"], "topic_key": p.get("topic_key"),
           "title": " ".join(re.sub(r"<[^>]+>", " ", first.get("headline") or first.get("title") or "").split()),
           "item_ids": p.get("item_ids", []), "media_id": mid, "url": m.get("permalink"),
           "slides": slides, "caption_exact": (m.get("caption") or "").strip() == p["caption"].strip(),
           "published_at": dt.datetime.now(zone).isoformat(timespec="seconds")}
    ledger.append(rec); ledger_f.parent.mkdir(parents=True, exist_ok=True)
    ledger_f.write_text(json.dumps(ledger, ensure_ascii=False, indent=1))
    print(json.dumps(rec, ensure_ascii=False), flush=True)
    if not rec["caption_exact"] or slides != len(urls): print(f"WARNING {p['id']}: read-back mismatch", file=sys.stderr)
    if p is not posts[-1]:
        time.sleep(a.gap)
