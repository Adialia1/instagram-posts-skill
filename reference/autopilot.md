# Autopilot: one post per run, no human in the loop

A scheduled cloud routine (for example Claude Code's scheduled routines, every 2 hours in the
daytime) publishes ONE post per run. Nobody reviews the post before it is public, so the automated
gates are the only review. **When in doubt, post nothing: a skipped slot costs nothing, a false
post costs the page.**

Setup for the routine: the skill must be in the repository the routine checks out (for example
`.claude/skills/instagram-posts/`), the routine's environment needs `KIE_API_KEY`, and the routine
needs the **Composio MCP connector** with Instagram connected (INSTALL.md, step 6). Paths below:
`SKILL=.claude/skills/instagram-posts`, `S=$SKILL/scripts`, `P=$SKILL/venv/bin/python`.

## DRY RUN (test the whole pipeline without posting)
If the prompt says **DRY RUN**: skip step 1's stop rules (cap, spacing, quiet hours) but still run
step 1 (it proves the connector); do steps 2–7 exactly; in step 8 run ONLY the first cell (it builds
the containers on Instagram, which expire unpublished) and STOP: never generate or run cell 2, never
call media_publish. Report "DRY RUN: not published", the container id and every slide's file name.

## PREVIEW (show the post as a page instead of posting it)
If the prompt says **PREVIEW**: like DRY RUN, but do not touch Instagram after step 1. Step 8 is:
`$P $S/preview_page.py $DAY` → `$DAY/preview.html` (every slide embedded, the caption, sources,
checks, and the rejected candidates: write those to `$DAY/rejected.json` as
`[{"candidate", "reason"}]` first). Share that file (for example as an Artifact) and put the link
at the top of the report.

## Every run, in order
0. **Setup and health**: `bash $S/setup.sh`. Anything but `READY` → stop, post nothing.
   `export IG_DAILY_HOME=$HOME/ig; BASE=$IG_DAILY_HOME; DAY=$BASE/$(date +%F-%H%M)`.

   **Instagram in the cloud = the Composio MCP connector.** No script can call a connector, so
   `ig_workbench.py` writes Python for the connector's `COMPOSIO_REMOTE_WORKBENCH` tool (pass the
   file's content as `code_to_execute`); you run it and copy **only the single line that starts
   with `@@RESULT@@`** from the tool's output into a file (write it with a quoted heredoc, exactly);
   the script reads that file back and verifies. (Locally, `posted.py` / `publish.py` do the same
   through the Composio CLI.)

1. **What is already on the account** (this also proves the connector works):
   `$P $S/ig_workbench.py posted-code > $BASE/cell.py` → run it in COMPOSIO_REMOTE_WORKBENCH → save
   the output to `$BASE/posted.txt` → `$P $S/ig_workbench.py posted-save $BASE/posted.txt $BASE`.
   If this fails, stop. Stop without posting if: `publish.max_per_day` posts already today (brand
   timezone), or the last post is younger than `publish.min_minutes_between_posts`, or the time is
   inside `publish.quiet_hours`.

2. **Pick the slot** by the hour of this run (`content-plan.md`, your grid). If its source yields
   nothing that passes, fall back to a data slot; if that fails too, post nothing.

3. **Research**: `$P $S/radar.py $BASE --days 7`, read `$BASE/radar/<date>.md`, take the top 3
   uncovered candidates for the slot. For news: read the articles (WebSearch / WebFetch) and keep a
   story only if **two independent outlets** (or the primary source) agree on every number you will
   print. For your data: `$P $S/datasource.py top|stats`, then `validation.md` line by line.

4. **Pictures**: people named → `$P $S/person.py $DAY p-<slug> "<name>"` (real photo or no face).
   Scenes → `$P $S/art.py $DAY <name> "<scene>"`. Never an AI face of a real person.

5. **Write** `$DAY/posts.json` with ONE post, id `p1` (`posts-schema.md`), shaped like
   `examples/demo/posts.json`; `facts` = every caption number not on a slide; the source named in
   the caption; `brand.copy.disclaimer` on anything that reads like financial advice.

6. **Build and gate**: `$P $S/slides.py $DAY && node $S/render.cjs $DAY && $P $S/check.py $DAY`
   (`posted.json` is next to the day, so check.py also refuses a repeat). Then Read every
   `$DAY/png/*.png` and look: reading order, number direction, nothing clipped, a face is a face.
   Any doubt → fix and rebuild, or post nothing.

7. **Check the items shown** (if any): `$P $S/datasource.py check '<expect_prices JSON>'` must exit 0.

8. **Publish** (two workbench cells, each well under the cell time limit):
   - `$P $S/ig_workbench.py publish-code $DAY p1 > $DAY/cell1.py` (uploads the JPEGs to kie.ai) →
     run → save the output to `$DAY/c1.txt` (the container id).
   - `$P $S/ig_workbench.py publish-code2 $DAY/c1.txt $DAY p1 > $DAY/cell2.py` → run → save to `$DAY/c2.txt`.
   - `$P $S/ig_workbench.py record $DAY/c2.txt $DAY p1 --ledger $BASE/ledger.json` must print
     VERIFIED. On "action is blocked" or any error: do NOT retry (cell 2 already checks whether the
     post went live). End the run.

9. **Report** (the run's final message): the post's link, the slot, the sources, the checks that
   passed, and every candidate rejected with the reason. That message is the run's log.

## Never
- Never post two in one run, never retry a failed publish, never exceed the daily cap.
- Never post a story you could not confirm twice, an item you did not check, or a number that is
  not on a slide or in `facts`.
- Never touch anything but Instagram: no commits, no pushes, no database writes.
