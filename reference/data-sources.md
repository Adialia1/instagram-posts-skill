# Data sources: your own numbers, behind one interface

The "our data" series (top-N, price cuts, the day in numbers) read your data through
`scripts/datasource.py`, which loads the module named in `brand.json` → `"data_source"`
(default `scripts/sources/mock.py`).

## The shipped source: mock data
`data/mock-listings.json` holds 28 **invented** real-estate listings in four made-up places. Nothing
in it is a real property. Four of them are deliberate traps, the same kinds of error that real
listing data contains, so you can watch validation catch them:

| id | trap | what catches it |
|---|---|---|
| `demo-901` | a sale price filed under rent (it tops the rent list) | reading the description (validation.md) |
| `demo-902` | a placeholder price (123,456) | `datasource.py` drops known placeholders |
| `demo-903` | the same house from a second advertiser | `datasource.py` drops exact duplicates |
| `demo-904` | price 0 = "on request" | never enters a statistic |

## The schema an item needs
```jsonc
{"id": "demo-019", "city": "Old Town", "neighbourhood": "Market Square",
 "category": "sale",                 // sale | rent
 "property_type": "house", "rooms": 5, "size_m2": 285,
 "price": 3948000, "currency": "USD", // 0 = unstated
 "created_at": "2026-09-14",          // when it was published (not when you first saw it)
 "price_history": [{"date": "2026-09-14", "price": 3948000}],
 "status": "live",                    // live | gone (gone = confirmed at the source, not "missing from a sweep")
 "description": "..."}
```
Other domains work the same way (cars, products, jobs, rentals): keep `id`, `price`, `status`,
`created_at`, `price_history`, `description`, and rename the rest in your queries and slides.

## Plug in your own
Write a module with two functions and point `brand.json` at it:
```python
# scripts/sources/mine.py
def listings():            # -> list[dict] in the schema above
    ...                    # read your DB / CSV / API here
def check(expected):       # expected: {id: price}; -> {id: {"live": bool, "price": number|None}}
    ...                    # ask the SOURCE OF TRUTH (the live page or API), never a cached copy
```
```json
"data_source": "scripts/sources/mine.py"
```
Rules that matter more than the code:
- **Liveness comes from the source of truth.** A "last seen" date in your own copy is not proof an
  item is still up; `check()` must ask the live page/API.
- **Some sites block plain HTTP clients.** If yours does, add what you need to `requirements.txt`
  (for example `curl_cffi` for browser-like TLS) and respect the site's terms.
- **Secrets stay in environment variables**, never in `brand.json` or the repo.
- An MCP database connector works too: in an agent run, query it, save the rows to a JSON file in
  the schema above, and point a tiny source module at that file.
