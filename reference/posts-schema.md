# posts.json, one file per day

Location: `$IG_DAILY_HOME/<YYYY-MM-DD>/posts.json`, art in `art/<name>.jpg` next to it. The ledger is
`../ledger.json` (shared by all days). Worked examples: `examples/demo/posts.json` and
`examples/demo-he/posts.json`; their renders are in `jpg/` beside them.

```jsonc
{
 "date": "2026-10-01",
 "posts": [{
  "id": "p1",                        // p1..p10, also the slide file prefix
  "time": "16:00",                   // the slot from content-plan.md
  "series": "Top 3 · our data",
  "topic_key": "top:priciest-homes:2026-10",   // unique forever; check.py refuses a repeat
  "item_ids": ["demo-019"],          // every item from your data source shown; the ledger keeps them
  "expect_prices": {"demo-019": 3948000},      // fed to datasource.py check before publishing
  "slides": [ ... ],
  "caption": "...",                  // plain text, real newlines, raw # hashtags
  "facts": ["1.10.2026"],            // numbers the caption may use that are not on a slide
  "data": ["what was queried"],      // shown in the review sheet; required
  "checks": ["what was verified, with results"],   // required
  "sources": ["URLs or table names"] // required
 }]
}
```

## Slide types (all text is HTML: `<span class="o">` = accent colour, `<br>` = line break)

| type | fields |
|---|---|
| `news` | `art`, `headline` (≤ 3 lines), `insets: [{art \| flag \| person, at, size}]` (0–2 round insets), `credit` (default `brand.copy.credit_default`), `size` (headline px, default 104), `photo_h` (default 860) |
| `news_text` | `art`, `title`, `body` (`<b>` = accent; ≤ ~40 words), `title_lines` (default 1), `size` (title px, default 96), `photo_h` (default 720) |
| `item` | `art`, `rank` ("01"), `title`, `detail`, `value` (the number, shown in the accent colour), `unit`, `size`, `value_size` |
| `news_end` | optional `headline`, `cta`, `size`; defaults from `brand.copy` |

Insets: `flag` is one of `il us uk fr de jp` (add more in `slides.py` FLAGS); `art` is a picture from
`art.py --shape circle`; `person` is a slug made by `person.py` (its photo credit is added to the
slide automatically). `at`: `te` top-end, `ts` top-start, `me` / `ms` middle-end / middle-start
("start" is the reading start: the left in English, the right in Hebrew).

Rules the builder enforces: number ranges ("24.9–30.9", "1–5") are isolated left-to-right
automatically. Wrap any other number that sits next to RTL punctuation in `<span class="n">…</span>`.

Lengths that fit: a `news` headline of 3 short lines at 104 px; a `news_text` body of ~40 words;
an `item` title of ~24 characters. `render.cjs` fails when text runs past the footer line.
