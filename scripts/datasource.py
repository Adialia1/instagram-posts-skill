#!/usr/bin/env python3
"""Your own data, behind one small interface, so the "our data" series work with any source.

    python3 datasource.py top   [--category sale|rent] [--by price|cut|size] [--n 5] [--city X]
    python3 datasource.py stats [--days 7]                 # new, price cuts, gone, in the window
    python3 datasource.py check '{"demo-004": 512000}'     # live? same price? (exit 1 on any mismatch)

The source is a Python module chosen by brand.json "data_source" (default: scripts/sources/mock.py,
invented listings). To plug in your own (a database, a CSV, an API), write a module with
`listings()` and `check(expected)`; see reference/data-sources.md.

`top` applies the safe defaults every list needs: live items only, no price 0 ("unstated"), no
placeholder prices, no exact duplicates. It does NOT read descriptions for you: a top-N row can
still be a sale filed as rent. Read every row before it goes on a slide (reference/validation.md).
"""
import argparse, datetime as dt, importlib.util, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import BRAND, skill_path

PLACEHOLDERS = {123456, 1234567, 111111, 999999, 1, 10, 100}


def source():
    path = skill_path(BRAND.get("data_source") or "scripts/sources/mock.py")
    spec = importlib.util.spec_from_file_location("ig_source", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def clean(rows):
    seen, out = set(), []
    for x in rows:
        if x.get("status") != "live" or not x.get("price") or x["price"] in PLACEHOLDERS:
            continue
        sig = (x.get("city"), x.get("neighbourhood"), x.get("price"), x.get("size_m2"), x.get("rooms"))
        if sig in seen:          # same place, price, size and rooms: one property from two advertisers
            continue
        seen.add(sig); out.append(x)
    return out


def cut(x):
    h = x.get("price_history") or []
    return (h[0]["price"] - h[-1]["price"]) if len(h) > 1 and h[0]["price"] else 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["top", "stats", "check"]); ap.add_argument("arg", nargs="?")
    ap.add_argument("--category", default="sale"); ap.add_argument("--by", default="price", choices=["price", "cut", "size"])
    ap.add_argument("--n", type=int, default=5); ap.add_argument("--city"); ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    src = source()
    if a.cmd == "check":
        expected = json.loads(a.arg or sys.stdin.read())
        res = src.check(list(expected))
        bad = 0
        for i, want in expected.items():
            r = res.get(i, {"live": False, "price": None})
            ok = r["live"] and (want is None or r["price"] == want)
            bad += not ok
            print(f'{"OK  " if ok else "FAIL"} {i}: live={r["live"]} price={r["price"]} expected={want}')
        sys.exit(1 if bad else 0)
    rows = src.listings()
    if a.cmd == "top":
        rows = [x for x in clean(rows) if x.get("category") == a.category and (not a.city or x.get("city") == a.city)]
        key = {"price": lambda x: x["price"], "cut": cut, "size": lambda x: x.get("size_m2") or 0}[a.by]
        rows = sorted(rows, key=key, reverse=True)[:a.n]
        print(json.dumps([{**x, "cut": cut(x)} for x in rows], ensure_ascii=False, indent=1))
    else:
        dates = [dt.date.fromisoformat(x["created_at"]) for x in rows if x.get("created_at")]
        end = max(dates) if dates else dt.date.today(); start = end - dt.timedelta(days=a.days - 1)
        inwin = lambda d: start <= dt.date.fromisoformat(d) <= end
        new = [x for x in rows if inwin(x["created_at"])]
        cuts = [x for x in rows if len(x.get("price_history") or []) > 1 and inwin(x["price_history"][-1]["date"]) and 0 < cut(x) <= 0.5 * x["price_history"][0]["price"]]
        print(json.dumps({"window": f"{start}..{end}", "new": len(new), "price_cuts": len(cuts),
                          "gone": sum(x.get("status") == "gone" for x in rows), "total": len(rows)}, indent=1))


if __name__ == "__main__":
    main()
