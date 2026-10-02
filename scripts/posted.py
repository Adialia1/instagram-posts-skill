#!/usr/bin/env python3
"""What is already on the account? Read from Instagram itself: the source of truth, also in a
cloud run where no local ledger exists.

    python3 posted.py [<out_dir>] [--n 60]
      -> <out_dir>/posted.json  [{id, timestamp, local_time, caption, hook, permalink, type, slides}]
      prints today's count (brand timezone), the last post's time, and the recent hooks

Run it before planning: never repeat a story whose hook matches a recent post, and respect the
daily cap. check.py reads <day>/../posted.json to refuse a repeated headline.
"""
import argparse, datetime as dt, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import home, ig_user_id, tz
from composio_connect import ig_call

ap = argparse.ArgumentParser(); ap.add_argument("out", nargs="?"); ap.add_argument("--n", type=int, default=60)
a = ap.parse_args()
out = pathlib.Path(a.out).expanduser() if a.out else home(); out.mkdir(parents=True, exist_ok=True)
j = ig_call("GET", f"{ig_user_id()}/media?fields=id,caption,permalink,timestamp,media_type,children{{id}}&limit={a.n}")
zone = tz()
rows = []
for m in j.get("data", []):
    t = dt.datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(zone)
    cap = m.get("caption") or ""
    rows.append({"id": m["id"], "timestamp": m["timestamp"], "local_time": t.isoformat(timespec="minutes"),
                 "caption": cap, "hook": cap.split("\n")[0][:140], "permalink": m.get("permalink"),
                 "type": m.get("media_type"), "slides": len(m.get("children", {}).get("data", [])) or 1})
(out / "posted.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
today = dt.datetime.now(zone).date().isoformat()
n_today = sum(1 for r in rows if r["local_time"].startswith(today))
print(f"{len(rows)} recent posts · today ({today}) {n_today} · last at {rows[0]['local_time'] if rows else '-'}")
for r in rows[:30]:
    print(f'{r["local_time"][5:16]}  {(r["type"] or "")[:8]:8}  {r["hook"][:90]}')
