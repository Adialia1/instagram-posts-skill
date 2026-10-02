# Install and set up

Written so an AI agent (Claude Code or similar) can follow it top to bottom. A human can too.
The user only has to paste:

> Install the skill from https://github.com/Adialia1/instagram-posts-skill and set it up

**Agent: ask the user before each step marked 👤.** Never print, log or commit a key. Never
publish anything during setup: the last step is a DRY RUN.

## 1. Clone into a skills folder
Personal (all projects):
```bash
git clone https://github.com/Adialia1/instagram-posts-skill ~/.claude/skills/instagram-posts
```
Or per project (needed for a cloud routine, which only sees the repository it checks out):
```bash
git clone https://github.com/Adialia1/instagram-posts-skill .claude/skills/instagram-posts
rm -rf .claude/skills/instagram-posts/.git      # vendor it into your repo
```
Use `SKILL=<that folder>` below. Claude Code finds the skill by its `SKILL.md` (restart the session
if it doesn't show up).

## 2. Python and Node dependencies
```bash
cd "$SKILL"
python3 -m venv venv
venv/bin/pip install -r requirements.txt          # Pillow; add what your own data source needs
npm install --no-audit --no-fund                  # playwright 1.63.0 (pinned in package.json)
npx playwright install chromium                   # add --with-deps on a fresh Linux box
```
Alternative without `npm install`: `npx playwright@1.63.0 install chromium`. `render.cjs` also
finds Playwright in the npx cache.

## 3. 👤 kie.ai key (pictures + image hosting)
The user creates a key at https://kie.ai (API keys page) and adds credits (about $0.05 per picture).
Store it OUTSIDE the repo. Either:
```bash
mkdir -p ~/.config/kie && (umask 077; cat > ~/.config/kie/api_key)   # paste the key, then Ctrl-D
```
or export `KIE_API_KEY` in the shell profile / the cloud routine's environment. Never pass it as a
command-line argument.

## 4. 👤 Connect Instagram through Composio
Requirements: an Instagram **professional** account (Business or Creator). A Facebook page is not
needed: Composio uses "Instagram API with Instagram Login".

**Locally (Composio CLI):**
```bash
curl -fsSL https://composio.dev/install | bash   # installs the `composio` CLI
composio login                                   # opens the browser
composio link instagram                          # authorize the Instagram account
venv/bin/python scripts/composio_connect.py whoami --save    # prints the account, saves its id to brand.json
```
**In a cloud routine:** attach the **Composio MCP connector** to the routine (claude.ai → Settings
→ Connectors → Composio) and connect Instagram inside Composio. The routine uses
`scripts/ig_workbench.py` (reference/autopilot.md). Put the account id in `brand.json` →
`instagram_user_id` (from `whoami` above, or ask the connector for `GET me?fields=user_id,username`).

Alternative for scripts without the CLI: set `COMPOSIO_CONSUMER_API_KEY` (a `ck_...` key from the
Composio dashboard) and `composio_connect.py` calls Composio's MCP endpoint directly.

## 5. 👤 Fill in brand.json
Ask the user for: brand name (`name` + `name_bold`, shown as the wordmark), `handle`, `site`,
`lang` (`en`, `he`, ...), `timezone` (IANA, for example `Europe/London`), the accent colour, and a
logo (`assets/logo.svg`, a square SVG or PNG). Then:
- `copy`: the credit line, end-slide strings, `banned_words` (competitors, anything never to name),
  and `disclaimer`.
- `publish`: `max_per_day` (≤ 9 is safe), `gap_seconds`, `min_minutes_between_posts`, `quiet_hours`.
- `radar`: search `queries` per language, optional RSS `feeds`, and `topic_words` (a regex) for the niche.
- `data_source` (optional): your own module (reference/data-sources.md). Without it, the mock data is used.
- Fonts: the shipped ones (Noto Sans Hebrew + Heebo, OFL) cover Latin and Hebrew. For other fonts,
  put the woff2 files and a `fonts.css` in `assets/fonts/` and set `fonts.css`, `fonts.headline`
  and `fonts.body`. Use fonts whose licence allows it, and include the licence file.

## 6. Prove it works
Before running the build on a machine you share with other projects, check for injected build
config (any output means stop and investigate):
```bash
find . \( -name "*.config.js" -o -name "*.config.mjs" -o -name "*.config.cjs" -o -name "*.config.ts" \) \
  -not -path "*/node_modules/*" -exec awk 'length($0)>2000{print FILENAME": line "FNR; exit}' {} +
```
Then:
```bash
bash scripts/setup.sh                                  # must end with READY
P=venv/bin/python
$P scripts/slides.py examples/demo && node scripts/render.cjs examples/demo && $P scripts/check.py examples/demo
IG_BRAND=examples/demo-he/brand.he.json $P scripts/slides.py examples/demo-he && \
  IG_BRAND=examples/demo-he/brand.he.json node scripts/render.cjs examples/demo-he
```
Open `examples/demo/png/` and check that the slides match `examples/demo/jpg/` (your brand.json
changes the colours, logo and wordmark).

## 7. DRY RUN (builds everything, publishes nothing)
Ask Claude Code:
> Use the instagram-posts skill: make ONE post for today. DRY RUN: build and check it, create the
> Instagram container, and do not publish.

It researches, validates, renders and runs `publish.py <day> --dry-run --only p1`, which uploads the
JPEGs and creates the container on Instagram without publishing (the container expires on its own).
Report the result to the user. Publishing for real is always the user's decision.

## 8. Optional: autopilot (cloud routine)
Commit the skill into the repository the routine checks out (`.claude/skills/instagram-posts/`),
add `KIE_API_KEY` to the routine's environment, attach the Composio MCP connector, and schedule a
routine (Claude Code: `/schedule`) with a prompt like:

```text
Run the instagram-posts skill in autopilot mode: follow .claude/skills/instagram-posts/reference/autopilot.md
exactly, from step 0. Publish at most ONE post. If any gate fails or anything is uncertain, post
nothing and report why. Do not commit, push, or change anything except Instagram.
```
Start with `DRY RUN` (or `PREVIEW`) added to the prompt for the first few runs. Remove it only once
the dry runs look right.
