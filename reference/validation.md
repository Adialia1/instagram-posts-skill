# Validation: what every number must pass

Every rule below exists because a real run caught a false claim with it that would otherwise have
been posted. A slot that fails any line is dropped, and the review (or the run's report) says why.

## Items from your own data
- [ ] **Check every item shown against the source of truth** (`datasource.py check`). A "last
      seen" date is not liveness: filtering on it once hid the two most expensive live items and
      crowned the third.
- [ ] The live price equals the price on the slide. Re-check immediately before publishing.
- [ ] **Duplicates**: the same property from two advertisers (same place, ~same size, same price).
      Show one, or say so.
- [ ] **Outliers**: price per m² against the area's median. A price 10× its neighbours is usually a
      typo (8.5M typed as 85M). Confirm on the item itself before calling it a record.
- [ ] **Not what it says it is**: read the description of every top-N row. A "house" can be a
      working hotel; a "rent" can be a sale filed in the wrong category; a price can be a placeholder.
- [ ] Price 0 / "on request" never enters a statistic.

## Counts and changes
- [ ] Count **items, not events**: for "price cuts this week" compare each item's first and last
      price in the window; drop changes over 50 % (typos) and zeros.
- [ ] Windows are whole days in the brand's timezone, and the window is written on the slide.
- [ ] "New" means published in the window (`created_at`), not "first seen by us".
- [ ] "Gone" means confirmed gone at the source. Write "taken down", never "sold": you do not know why.
- [ ] Spot-check a random sample of ≥ 20 against the source; put the result in `checks` ("19/20 match").
- [ ] Does one outlier carry the total?

## Places
- [ ] Coordinates shared by many items are an area's centroid, not an address: never use them for distances.
- [ ] Name things truthfully: "near the sea" not "on the beach"; "town" not "city" for a village.
- [ ] OpenStreetMap data → "© OpenStreetMap contributors" in the caption (ODbL).

## News, official data and stories
- [ ] Official figure: the exact number, period and publisher, with the URL in `sources`.
- [ ] News: **two independent outlets** (not two outlets relaying one exclusive) or the primary
      source, and read the article's own date (a 2017 article can carry a "© 2026" footer).
- [ ] Reject: rumours, denials, advertorials, a reporter's projection sold as fact, asking prices
      presented as a market.
- [ ] Every fact in a story has a source URL. Living people: public facts only, nothing defamatory.
- [ ] Explainers: an official page for the current year; if two official pages disagree, skip.

## Copy (enforced by `scripts/check.py`)
- [ ] Every caption number is on a slide or in `facts`.
- [ ] No banned words (`brand.json` → `copy.banned_words`), no em dash, `data`/`checks`/`sources` filled.
- [ ] AI art is credited as illustrative and never stands in for a specific real property or person.
- [ ] Never a private person's name, phone number or exact address, and never a photo you do not
      have the rights to (listing photos belong to the advertiser; agency photos are licensed).
