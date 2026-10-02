---
name: instagram-posts
description: Research, validate, design and publish Instagram news posts for a brand: one post (or a day's set) in one consistent "news" look (a vivid photo, round insets, the brand wordmark on a divider, a black band with a condensed headline and accent words), with every number checked before it is shown. Works in English or Hebrew/RTL, from your own data source plus news and official sources, published through Composio. Use when asked for today's Instagram post(s), a data post / top-N / news story / explainer for Instagram, to publish approved posts, to dry-run the pipeline, or to run the posting routine unattended.
---

# Instagram posts (research → validate → design → publish)

The page works like a news brand: a fixed schedule of series, each filled with something true and
new. **Validation is the product**: a wrong number on a public post cannot be edited away (the
Instagram API has no caption edit and no delete), and in real use research rejects about 40 % of
candidates. When in doubt, post nothing.

Worked examples: `examples/demo/` (English: a single and a top-3 carousel from the mock data) and
`examples/demo-he/` (Hebrew RTL carousel, with its own `brand.he.json`). Each has `posts.json`, the
art, and `jpg/` showing how the slides must look. Read one before writing a post.

## Files
| | |
|---|---|
| `brand.json` | name, handle, site, colours, fonts, logo, copy strings, banned words, publish limits, radar queries, timezone |
| `reference/content-plan.md` | the daily slots, the series bank, sources, uniqueness |
| `reference/validation.md` | the checklist every number passes, and why each line exists |
| `reference/data-sources.md` | the listing schema, the mock source, how to plug in your own |
| `reference/posts-schema.md` | the `posts.json` format and the four slide types |
| `reference/autopilot.md` | the unattended run (cloud routine): one post per run, its gates, DRY RUN and PREVIEW |
| `scripts/setup.sh` | installs and proves every dependency; anything but READY = post nothing |
| `scripts/datasource.py` | your data: `top`, `stats`, `check` (live + price) through the configured source |
| `scripts/radar.py` | the news radar: Google News + feeds → scored stories, marks what you covered |
| `scripts/art.py` | one picture for a slide (kie.ai); never text in the picture |
| `scripts/person.py` | a real, free-licensed photo of a named public figure (Wikimedia) + its credit |
| `scripts/slides.py` | posts.json → HTML slides in the brand's look |
| `scripts/render.cjs` | HTML → PNG + JPEG; fails on a missing font/image or text past the safe area |
| `scripts/check.py` | the copy gate: caption numbers, sources filled, banned words, em dash, repeats |
| `scripts/review.py` / `preview_page.py` | the review sheet (attended) / a self-contained preview page |
| `scripts/composio_connect.py` | Instagram API through Composio (CLI, or a `ck_` consumer key); `whoami` |
| `scripts/posted.py` | what is on the account now (from Instagram itself): dedupe + daily count |
| `scripts/publish.py` | host images on kie.ai + publish + ledger; refuses without `--yes` or `--dry-run` |
| `scripts/ig_workbench.py` | Instagram through the Composio MCP connector (cloud routine) |
| `scripts/insights.py` | your own posts' reach/likes/saves/shares into the ledger |

`S=<this skill folder>/scripts`. Run Python with the skill's venv: `$SKILL/venv/bin/python`.
Working folder: `$IG_DAILY_HOME` (default `~/instagram-daily`): one folder per day
(`<base>/<YYYY-MM-DD>/`), `ledger.json`, `posted.json` and `radar/` beside them.

## Two ways to run
- **Attended** (a person in the chat): the steps below; they approve the review sheet before publishing.
- **Autopilot** (a scheduled cloud routine): `reference/autopilot.md`, one post per run, no
  approval, so the automated gates are the only review.

## Steps
0. **Intake**: `$S/posted.py` (what is already up), `$S/radar.py` (stories of the last days),
   `$S/insights.py` (which series work). Read the reports before planning.
1. **Plan** with `content-plan.md` and the ledger: pick a series per slot. Fewer good posts beat a
   full grid with a weak one. Pick 1.5× the candidates you need: many will fail validation.
2. **Research** each slot: `datasource.py top|stats` for your data; for news, read the articles
   themselves (WebSearch/WebFetch or a search MCP) and keep every query and URL.
3. **Validate** with `validation.md`, line by line. `datasource.py check '{"<id>": <price>}'` for
   every item shown. A slot that fails is dropped; note why.
4. **Write `posts.json`** (`posts-schema.md`). Copy rules: the brand's language, no banned words,
   no em dash, the source named in the caption ("according to ..."), `copy.disclaimer` on anything
   that reads like financial advice. `facts` = every caption number that is not on a slide.
5. **Art** for each new picture, in parallel (75–160 s each): `$S/art.py <day> <name> "<scene>" &`.
   People named in a post: `$S/person.py <day> p-<slug> "<name>"` (real photo or no face). Look at
   every picture: no text, no logo, nothing pretending to be a specific real property or person.
6. **Build and gate**: `$S/slides.py <day> && node $S/render.cjs <day> && $S/check.py <day> && $S/review.py <day>`.
   All must pass. Then LOOK at every PNG: reading order (RTL), number direction, nothing clipped.
7. **Review** (attended): open `<day>/review.html`, say what is in it and what was rejected, and
   wait for approval of specific posts.
8. **Publish** only what was approved: re-run `datasource.py check` (prices move), then
   `$S/publish.py <day> --yes --only p1,p3`. It reads each post back and writes the ledger. Report the links.
   **Dry run**: `$S/publish.py <day> --dry-run --only p1` builds the containers and never publishes.

## The look
Four slide types only (`check.py` refuses others): `news` (cover or single), `news_text` (inner
story slide), `item` (one thing per slide, for top-Ns), `news_end` (follow slide). Colours, fonts,
logo and wordmark come from `brand.json`; `"lang": "he"` (or another RTL language) mirrors the
layout. **Never let an image model draw text or numbers**: `art.py` makes the picture,
`slides.py` typesets every word.

## Traps
- **Instagram blocks bursts.** About 20 posts in 40 minutes earned "action is blocked" (code 4 /
  subcode 2207051). `publish.py` caps posts per day (`publish.max_per_day`) and waits between posts.
  Never retry into a block.
- **An error on media_publish does not mean it failed**: a "blocked" post can still go live.
  `publish.py` looks for the caption on the account before calling it a failure, so a retry cannot duplicate.
- **No edit, no delete** through the API, and **no music**: music on a photo or carousel exists only
  in the phone app. Approval (or the autopilot's gates) comes first.
- **Top-N lists surface data errors first**: a sale filed as rent, a placeholder price, a duplicate
  from a second advertiser. Read every row's description (the mock data has all three on purpose).
- **Old news looks new**: check the article's own date, not the page footer. Two independent outlets
  or the primary source, or it is not posted.
- kie.ai rejects aspect 4:5; `art.py` asks for 3:4 and crops. Uploads expire after 24 h (fine for Instagram).
- Composio's Instagram connection is "Instagram API with Instagram Login": the host is
  `graph.instagram.com`, and a JSON body sends a raw `#`.
- Never put a personal email or a key in a request header, a URL, or a command line.
