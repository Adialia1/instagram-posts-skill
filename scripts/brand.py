"""Shared settings for every script: the brand (brand.json), the working folder and the Instagram account.

    from brand import BRAND, SKILL, home, tz, ig_user_id, composio_cli

Nothing about an account is hard-coded anywhere else. Override with environment variables:
  IG_BRAND        path to another brand.json (default: <skill>/brand.json)
  IG_DAILY_HOME   working folder for days, ledger.json, posted.json, radar/ (default: ~/instagram-daily)
  IG_USER_ID      the Instagram user id (default: brand.json "instagram_user_id")
  COMPOSIO_CLI    path to the composio binary (default: found on PATH, then ~/.local/bin/composio)
"""
import json, os, pathlib, shutil, sys
from zoneinfo import ZoneInfo

SKILL = pathlib.Path(__file__).resolve().parents[1]
BRAND_FILE = pathlib.Path(os.environ.get("IG_BRAND") or SKILL / "brand.json")
BRAND = json.loads(BRAND_FILE.read_text())


def skill_path(p):
    """A path from brand.json: absolute, ~, or relative to the skill folder."""
    p = pathlib.Path(p).expanduser()
    return p if p.is_absolute() else SKILL / p


def home():
    h = pathlib.Path(os.environ.get("IG_DAILY_HOME") or "~/instagram-daily").expanduser()
    h.mkdir(parents=True, exist_ok=True)
    return h


def tz():
    return ZoneInfo(BRAND.get("timezone") or "UTC")


def rtl():
    return BRAND.get("lang", "en") in ("he", "ar", "fa", "ur", "yi")


def ig_user_id():
    uid = os.environ.get("IG_USER_ID") or BRAND.get("instagram_user_id")
    if not uid:
        sys.exit("no Instagram user id: run `python3 scripts/composio_connect.py whoami --save` "
                 "or set IG_USER_ID / brand.json instagram_user_id")
    return str(uid)


def composio_cli():
    c = os.environ.get("COMPOSIO_CLI") or shutil.which("composio") or str(pathlib.Path.home() / ".local/bin/composio")
    if not pathlib.Path(c).exists():
        sys.exit("composio CLI not found: install it (see INSTALL.md) or set COMPOSIO_CLI")
    return c


IG_API = "https://graph.instagram.com/v21.0"
