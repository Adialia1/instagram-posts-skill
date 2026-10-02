"""The demo data source: data/mock-listings.json (invented listings, a few deliberate data traps).

A data source is any module with these two functions; copy this file to start your own.

    listings() -> list[dict]          every item, in the schema of reference/data-sources.md
    check(expected: dict) -> dict     {id: {"live": bool, "price": number | None}} for the ids asked,
                                      read from the SOURCE OF TRUTH (the live page/API), not a cache
"""
import json, pathlib

FILE = pathlib.Path(__file__).resolve().parents[2] / "data/mock-listings.json"


def listings():
    return json.loads(FILE.read_text())["listings"]


def check(expected):
    by_id = {x["id"]: x for x in listings()}
    out = {}
    for i in expected:
        x = by_id.get(i)
        out[i] = {"live": bool(x) and x["status"] == "live", "price": x["price"] if x else None}
    return out
