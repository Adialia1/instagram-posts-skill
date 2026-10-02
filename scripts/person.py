#!/usr/bin/env python3
"""A real, freely licensed photo of a public figure for a round inset, with its credit.

    python3 person.py <day_dir> <slug> "<name>" [--focus 0.22] [--zoom 1.0] [--cx 0.5] [--qid Q...]
      -> <day_dir>/art/<slug>.jpg (600x600, face-biased square crop)
         <day_dir>/art/<slug>.credit.json  {"name","file","artist","license","credit","source"}

The rules:
- Only Wikimedia Commons, only licences that allow commercial use with credit: CC0, public
  domain, CC BY, CC BY-SA (any version). Anything else is refused.
- The credit goes on the slide automatically: "Media: <artist> / Wikimedia, CC BY-SA 4.0".
- NEVER an AI-generated face of a real person. No free photo means no face: use a flag, a
  place or an object instead.
- The licence covers the photographer's copyright, not the person's own rights: the person
  appears only in a news post ABOUT them, never next to your call to action or in a way that
  suggests they endorse you. The end slide never carries a face.

Lookup: Wikidata search -> the entity's P18 (image) -> Commons imageinfo (LicenseShortName,
Artist) -> a 900px thumbnail -> a square crop around the upper part of the frame (portraits put
the face there; --focus moves the crop centre, 0 = top). Look at the crop before using it.
"""
import argparse, html, json, pathlib, re, subprocess, urllib.parse, urllib.request

UA = {"User-Agent": "instagram-posts-skill/1.0 (person photo lookup; https://github.com)"}
OK = re.compile(r"^(cc0|public domain|pd|cc[- ]by(-sa)?[- ]?\d(\.\d)?|cc[- ]by(-sa)?)", re.I)

def get(url):
    # Wikimedia answers 429 to busy shared IPs (cloud runs). Back off and retry, honouring
    # Retry-After; if it still refuses, the caller posts with no face (the rule), never an AI face.
    import time, urllib.error
    for wait in (0, 20, 45):
        time.sleep(wait)
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25))
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            ra = e.headers.get("Retry-After")
            if ra and ra.isdigit(): time.sleep(min(int(ra), 60))
    raise SystemExit("wikimedia: rate-limited (429) after 3 tries: use no face")

def strip(h):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", h or "")).split())

ap = argparse.ArgumentParser(); ap.add_argument("day"); ap.add_argument("slug"); ap.add_argument("name")
ap.add_argument("--focus", type=float, default=0.22); ap.add_argument("--qid")
# --zoom < 1 crops tighter (a face small in a wide frame); --cx centres it horizontally (0..1)
ap.add_argument("--zoom", type=float, default=1.0); ap.add_argument("--cx", type=float, default=0.5)
a = ap.parse_args()
art = pathlib.Path(a.day) / "art"; art.mkdir(parents=True, exist_ok=True)

lang = "he" if re.search(r"[֐-׿]", a.name) else "en"
qids = [a.qid] if a.qid else [r["id"] for r in get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
    {"action": "wbsearchentities", "search": a.name, "language": lang, "type": "item", "limit": 5, "format": "json"}))["search"]]
found = None
for q in qids:
    ent = get(f"https://www.wikidata.org/wiki/Special:EntityData/{q}.json")["entities"][q]
    human = any(c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") == "Q5" for c in ent["claims"].get("P31", []))
    img = ent["claims"].get("P18")
    if human and img:
        found = (q, ent, img[0]["mainsnak"]["datavalue"]["value"]); break
if not found:
    raise SystemExit(f"no person with a Commons photo for {a.name!r} (candidates {qids}): use no face")
q, ent, fname = found
label = ent["labels"].get(lang, ent["labels"].get("en", {})).get("value", a.name)
ii = get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
    "action": "query", "titles": "File:" + fname, "prop": "imageinfo", "iiprop": "url|extmetadata",
    "iiurlwidth": 900, "format": "json"}))
info = next(iter(ii["query"]["pages"].values()))["imageinfo"][0]
md = info["extmetadata"]
lic = strip(md.get("LicenseShortName", {}).get("value"))
artist = strip(md.get("Artist", {}).get("value")) or "Unknown"
if not OK.match(lic):
    raise SystemExit(f"{fname}: licence {lic!r} is not free for commercial use: use no face")
artist = re.sub(r"\s*\(talk\).*$", "", artist)
# A credit line is read left to right; prefer the Latin form of the name when both are given
latin = re.search(r"\(([A-Za-z][^)]*)\)", artist)
artist = (latin.group(1) if latin and re.search(r"[\u0590-\u05FF\u0400-\u04FF]", artist) else artist)[:40]
# no contact details on a slide: "Jane Doe (jdoe at example mail)" -> "Jane Doe"
artist = re.sub(r"\s*\([^)]*(@|\bat\b|gmail|mail|www\.|https?:)[^)]*\)", "", artist, flags=re.I).strip()
raw = art / f"{a.slug}.raw.jpg"
# upload.wikimedia.org answers 403 to a request without a User-Agent
raw.write_bytes(urllib.request.urlopen(urllib.request.Request(info["thumburl"], headers=UA), timeout=30).read())
from PIL import Image  # Pillow, not ffmpeg: a cloud sandbox may not have ffmpeg
img = Image.open(raw).convert("RGB"); w, h = img.size
side = int(min(w, h) * a.zoom)
y = int(max(0, min(h - side, a.focus * h - side * 0.15)))
x = int(max(0, min(w - side, a.cx * w - side / 2)))
img.crop((x, y, x + side, y + side)).resize((600, 600)).save(art / f"{a.slug}.jpg", quality=90)
raw.unlink()
lic_short = lic.replace("Public domain", "PD")
credit = {"name": label, "qid": q, "file": fname, "artist": artist, "license": lic,
          "credit": f"Media: {artist} / Wikimedia, {lic_short}",
          "source": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(fname.replace(" ", "_"))}
(art / f"{a.slug}.credit.json").write_text(json.dumps(credit, ensure_ascii=False, indent=1))
print(json.dumps(credit, ensure_ascii=False))
