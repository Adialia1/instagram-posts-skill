#!/usr/bin/env python3
"""Instagram through the Composio MCP connector (a cloud routine), where no script can call the
connector itself: the script WRITES the code, the agent RUNS it with the connector's
COMPOSIO_REMOTE_WORKBENCH tool, saves the tool's output to a file, and the script READS it back
and verifies.

  # what is on the account (dedupe + daily count)
  python3 ig_workbench.py posted-code > cell.py              # run as code_to_execute, save output -> out.txt
  python3 ig_workbench.py posted-save out.txt $BASE          # -> $BASE/posted.json + summary

  # publish one post
  python3 ig_workbench.py publish-code $DAY p1 > cell1.py    # uploads the JPEGs to kie.ai, prints cell 1
  #   run cell 1, save output -> c1.txt; it ends with the container id
  python3 ig_workbench.py publish-code2 c1.txt $DAY p1 > cell2.py   # cell 2: publish + read back
  #   run cell 2, save output -> c2.txt
  python3 ig_workbench.py record c2.txt $DAY p1 --ledger $BASE/ledger.json   # verify + log

The workbench's preloaded `proxy_execute(method, endpoint, toolkit, body=...)` is the same proxy as
`composio proxy`; a JSON body sends a raw '#'. Each cell has a hard time limit (about 180 s), so
building containers and publishing are two cells. Everything a cell prints for us is ONE line:
'@@RESULT@@' + JSON. Copy only that line into the file.
"""
import datetime as dt, json, pathlib, re, shutil, sys, tempfile, uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import BRAND, ig_user_id

HELPERS = '''import json, time
UID = %r; TZ = %r; BASE = "https://graph.instagram.com/v21.0"
def call(m, path, body=None):
    res, err = proxy_execute(m, BASE + "/" + path, "instagram", body=body)
    if err: raise RuntimeError(f"{m} {path}: {err}")
    if isinstance(res, dict) and "error" in res: raise RuntimeError(f"{m} {path}: {res['error']}")
    return res
def wait(cid):
    for _ in range(45):
        st = call("GET", f"{cid}?fields=status_code").get("status_code")
        if st == "FINISHED": return
        if st in ("ERROR", "EXPIRED"): raise RuntimeError(f"container {cid}: {st}")
        time.sleep(3)
    raise RuntimeError(f"container {cid}: timed out")
def out(obj): print("@@RESULT@@" + json.dumps(obj, ensure_ascii=False))
'''


def helpers():
    return HELPERS % (ig_user_id(), BRAND.get("timezone") or "UTC")


def read_result(path):
    """Find the '@@RESULT@@{json}' line in whatever the agent saved (raw stdout or the tool's JSON wrapper)."""
    text = pathlib.Path(path).read_text()
    for _ in range(3):                      # unwrap JSON-in-JSON up to 3 levels
        try:
            j = json.loads(text)
            text = j["data"]["stdout"] if isinstance(j, dict) and "data" in j else (j if isinstance(j, str) else text)
            if not isinstance(text, str): break
        except Exception:
            break
    i = text.find("@@RESULT@@")
    if i < 0: sys.exit(f"no @@RESULT@@ in {path}: {text[:300]}")
    return json.loads(text[i + 10:].split("\n")[0])


def posts_of(day):
    day = pathlib.Path(day)
    return day, json.loads((day / "posts.json").read_text()), json.loads((day / "manifest.json").read_text())


cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "posted-code":
    # Compact on purpose: the agent copies the @@RESULT@@ line into a file by hand, and full captions
    # were too long to copy intact.
    print(helpers() + '''import datetime as dt
from zoneinfo import ZoneInfo
j = call("GET", f"{UID}/media?fields=id,caption,permalink,timestamp,media_type&limit=40")
zone = ZoneInfo(TZ); today = dt.datetime.now(zone).date().isoformat()
rows = []
for m in j.get("data", []):
    t = dt.datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(zone).isoformat(timespec="minutes")
    rows.append({"t": t, "type": (m.get("media_type") or "")[:4], "hook": (m.get("caption") or "").split("\\n")[0][:90]})
out({"today": sum(r["t"].startswith(today) for r in rows), "last": rows[0]["t"] if rows else None, "posts": rows})''')

elif cmd == "posted-save":
    r = read_result(sys.argv[2]); base = pathlib.Path(sys.argv[3]); base.mkdir(parents=True, exist_ok=True)
    rows = [{"local_time": x["t"], "type": x["type"], "hook": x["hook"], "caption": x["hook"]} for x in r["posts"]]
    (base / "posted.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print(f"{len(rows)} recent posts · today {r['today']} · last at {r['last']}")
    for x in rows[:20]: print(f'{x["local_time"][5:16]}  {x["type"]:4}  {x["hook"]}')

elif cmd == "publish-code":
    day, spec, man = posts_of(sys.argv[2]); pid = sys.argv[3]
    p = next(x for x in spec["posts"] if x["id"] == pid)
    import kie_image                       # public JPEG URLs Instagram can fetch (deleted by kie.ai after 24 h)
    key = kie_image.api_key()
    # kie.ai stores every upload by file name: use a name unique to this run so runs never overwrite each other
    tmp = pathlib.Path(tempfile.mkdtemp()); run = uuid.uuid4().hex[:8]
    def unique(n):
        dst = tmp / f"ig-{day.name}-{run}-{n[:-5]}.jpg"; shutil.copy(day / "jpg" / f"{n[:-5]}.jpg", dst); return dst
    urls = [kie_image.upload(unique(n), key) for n in man[pid]]
    plan = {"caption": p["caption"], "image_urls": urls}
    (day / f"{pid}.plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    print(helpers() + f"plan = json.loads({json.dumps(json.dumps(plan, ensure_ascii=False))})\n" + '''urls = plan["image_urls"]
if len(urls) == 1:
    cid = call("POST", f"{UID}/media", {"image_url": urls[0], "caption": plan["caption"]})["id"]
else:
    kids = [call("POST", f"{UID}/media", {"image_url": u, "is_carousel_item": True})["id"] for u in urls]
    for k in kids: wait(k)
    cid = call("POST", f"{UID}/media", {"media_type": "CAROUSEL", "children": kids, "caption": plan["caption"]})["id"]
wait(cid)
out({"container": cid, "slides": len(urls)})''')

elif cmd == "publish-code2":
    r = read_result(sys.argv[2]); day, spec, man = posts_of(sys.argv[3])
    cap = next(x for x in spec["posts"] if x["id"] == sys.argv[4])["caption"]
    print(helpers() + f"cid = {r['container']!r}\ncaption = {json.dumps(cap, ensure_ascii=False)}\n" + '''try:
    mid = call("POST", f"{UID}/media_publish", {"creation_id": cid})["id"]
    err = None
except Exception as e:
    # Instagram can answer "action is blocked" for a post it DID publish. Look before failing.
    err = str(e); time.sleep(20); mid = None
    recent = call("GET", f"{UID}/media?fields=id,caption&limit=5").get("data", [])
    mid = next((x["id"] for x in recent if (x.get("caption") or "").strip() == caption.strip()), None)
m = call("GET", f"{mid}?fields=id,permalink,caption,timestamp,children{{id}}") if mid else {}
out({"media_id": mid, "publish_error": err, "permalink": m.get("permalink"), "caption": m.get("caption", ""),
     "timestamp": m.get("timestamp"), "slides": len(m.get("children", {}).get("data", [])) or (1 if mid else 0)})''')

elif cmd == "record":
    r = read_result(sys.argv[2]); day, spec, man = posts_of(sys.argv[3]); pid = sys.argv[4]
    p = next(x for x in spec["posts"] if x["id"] == pid)
    ledger_f = pathlib.Path(sys.argv[sys.argv.index("--ledger") + 1]) if "--ledger" in sys.argv else day.parent / "ledger.json"
    exact = (r.get("caption") or "").strip() == p["caption"].strip()
    if not r.get("media_id") or not exact:
        sys.exit(f"NOT CONFIRMED: media_id={r.get('media_id')} caption_exact={exact} publish_error={r.get('publish_error')}. "
                 "Do not retry; report it.")
    first = p["slides"][0]
    rec = {"date": spec["date"], "id": pid, "series": p["series"], "topic_key": p.get("topic_key"),
           "title": " ".join(re.sub(r"<[^>]+>", " ", first.get("headline") or first.get("title") or "").split()),
           "item_ids": p.get("item_ids", []), "media_id": r["media_id"], "url": r["permalink"],
           "slides": r["slides"], "caption_exact": exact, "published_at": r.get("timestamp"),
           "note": ("publish answered an error but the post is live: " + r["publish_error"]) if r.get("publish_error") else None}
    ledger = json.loads(ledger_f.read_text()) if ledger_f.exists() else []
    ledger.append(rec); ledger_f.parent.mkdir(parents=True, exist_ok=True)
    ledger_f.write_text(json.dumps(ledger, ensure_ascii=False, indent=1))
    print(json.dumps(rec, ensure_ascii=False))
    print("VERIFIED" if rec["slides"] == len(man[pid]) else f"WARNING: {rec['slides']} slides live, {len(man[pid])} built")
else:
    sys.exit(__doc__)
