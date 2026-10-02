# Content plan

A news page grows on a **fixed schedule of series**, not on new ideas every day. Each slot is a
series with its own source and its own validation; the agent fills the slot with today's facts.
Followers learn what comes when. The grid below is an example for a real-estate page: change the
series, keep the method.

## An example daily grid
| # | Time | Series | Source | Format |
|---|---|---|---|---|
| 1 | 08:00 | **The day in numbers**: new items, price cuts, taken down | your data | single |
| 2 | 10:00 | **Local news**: today's story in your niche | news | single |
| 3 | 12:00 | **World**: a record, a famous name + a price, an oddity | news | single (+ person inset) |
| 4 | 14:00 | **The official figure**: one number from a statistics office or central bank | official | single or carousel |
| 5 | 16:00 | **Top N** (rotates: priciest, biggest cut, largest, cheapest in X) | your data | `item` carousel |
| 6 | 18:00 | **Story**: a person, a deal or a place told across slides | news | `news` + `news_text` carousel |
| 7 | 20:00 | **Explainer**: one rule explained (a tax, a contract clause) | official pages | carousel |
| 8 | 22:00 | **Engagement**: "guess the price", "which would you pick" | your data | carousel (answer on slide 2) |

If a slot has nothing that passes validation it is **skipped**, not filled with something weaker.
Mix singles and carousels through the day; carousels usually earn more saves.

## Finding stories
- `radar.py` every morning: stories of the last days, clustered, scored by outlets × recency × angle,
  with what you already covered marked. Tune `brand.json` → `radar.queries` / `feeds` / `topic_words`.
- Three time windows: **last 48 h** (breaking), **last month** (did well elsewhere, not posted by
  you), **evergreen** (old but still surprising; say when it happened, never present old news as today's).
- Read the article itself and take every number from it, not from a search snippet.
- Angles that travel: a famous name + a price; a record; a number that surprises; an official figure
  people argue about; "how much would it cost you".
- Learn from accounts you admire by reading their posts; never copy a post, a headline or a photo.

## Pictures and credits
Every slide carries ONE small credit line on the picture (`credit`):
`Media: AI · illustrative image` (the default) · `Media: <photographer>/<agency>` ·
`Media: <company>` for a company's own press photo.
A credit is attribution, NOT permission. Allowed without asking: AI art (`art.py`), flags, your own
screenshots, Wikimedia Commons under CC0/PD/CC BY/CC BY-SA (`person.py` handles credit + licence),
government press photos where their licence allows it, a company's press kit for its own project.
Needs a licence first: agency photos (Getty, Reuters, AP), listing photos (they belong to the
advertiser), TV screenshots, photos of private people.

## People
A person named in a post gets a round inset with a REAL photo from `person.py`, or no face at all
(a flag, a place or an object instead). Never an AI face of a real person. Never a face on the end
slide or beside your call to action (it reads as an endorsement).

## Uniqueness
Every post carries a `topic_key` (`top:priciest-homes:2026-10`, `news:<slug>:2026-10-01`).
`check.py` refuses a key already in the ledger and a caption hook too close to a recent post
(`posted.json`). Also avoid: the same item twice in 14 days, the same place leading two posts in a
day, two posts from one story.
