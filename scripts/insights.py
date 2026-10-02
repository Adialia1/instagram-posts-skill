#!/usr/bin/env python3
"""How did your own posts do? Pulls Instagram insights for every post in ledger.json and writes
them back, so planning can favour the series that work.

    python3 insights.py [<base_dir>]       -> updates ledger.json, prints a table by series

Metrics for feed posts: reach, likes, comments, saved, shares, views, total_interactions.
A post younger than ~48 h is still growing: compare series on posts at least 2 days old.
"""
import collections, datetime as dt, json, pathlib, statistics as st, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import home
from composio_connect import ig_call

base = pathlib.Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else home()
lf = base / "ledger.json"
if not lf.exists():
    sys.exit(f"no ledger at {lf}: nothing published yet")
ledger = json.loads(lf.read_text())
for e in ledger:
    j = ig_call("GET", f'{e["media_id"]}/insights?metric=reach,likes,comments,saved,shares,views,total_interactions', raise_on_error=False)
    if "error" in j:
        e["stats_error"] = str(j["error"].get("message", j["error"]) if isinstance(j["error"], dict) else j["error"])[:120]; continue
    e["stats"] = {m["name"]: (m.get("values") or [{}])[0].get("value", m.get("total_value", {}).get("value")) for m in j.get("data", [])}
    e["stats_at"] = dt.datetime.now().isoformat(timespec="minutes")
lf.write_text(json.dumps(ledger, ensure_ascii=False, indent=1))

print(f'{"date":10} {"series":18} {"reach":>6} {"likes":>5} {"saves":>5} {"shares":>6}  title')
for e in ledger:
    s = e.get("stats") or {}
    print(f'{e["date"]:10} {e["series"][:18]:18} {s.get("reach", "-"):>6} {s.get("likes", "-"):>5} {s.get("saved", "-"):>5} {s.get("shares", "-"):>6}  {(e.get("title") or "")[:50]}')
by = collections.defaultdict(list)
for e in ledger:
    if (e.get("stats") or {}).get("reach") is not None: by[e["series"]].append(e["stats"]["reach"])
print("\nmedian reach by series:", {k: st.median(v) for k, v in by.items()})
