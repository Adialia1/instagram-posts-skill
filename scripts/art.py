#!/usr/bin/env python3
"""Generate one picture for a slide and crop it.

    python3 art.py <day_dir> <name> "what the picture shows"                  # 4:5 photo -> art/<name>.jpg
    python3 art.py <day_dir> <name> "what the picture shows" --shape circle   # 1:1, for a round inset

A vivid, saturated editorial photograph, like a news site's lead image. GPT Image 2
through kie.ai (about 10 credits, ~$0.05), 75-160 s each: run several with `&`.
kie.ai rejects 4:5 although the model lists it, so we ask for 3:4 and crop.
The picture never carries text, numbers or logos (slides.py typesets those), never shows
a recognisable real person, and never pretends to be a specific real property: the slide's
credit line says it is an illustration.
"""
import argparse, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
NO = ("Absolutely no text, letters, numbers, signs, logos or watermarks anywhere in the image. "
      "No recognisable real person; people, if any, are anonymous or seen from behind.")
NEWS = ("Vivid, high-contrast, richly saturated editorial news photograph, like the lead image of a popular "
        "news site: sharp, bright, dramatic light, the subject large and immediately readable at phone size. " + NO)

ap = argparse.ArgumentParser()
ap.add_argument("day"); ap.add_argument("name"); ap.add_argument("what")
ap.add_argument("--shape", choices=["portrait", "circle"], default="portrait")
ap.add_argument("--ref", help="optional style reference image (local path or URL)")
a = ap.parse_args()
day = pathlib.Path(a.day); (day / "art").mkdir(parents=True, exist_ok=True)
png = day / "art" / f"{a.name}.png"
cmd = [sys.executable, str(HERE / "kie_image.py"), f"{a.what} {NEWS}",
       "--aspect", "1:1" if a.shape == "circle" else "3:4", "--resolution", "2K", "--out", str(png)]
if a.ref:
    cmd += ["--ref", a.ref]
subprocess.run(cmd, check=True)
from PIL import Image  # Pillow, not ffmpeg: a cloud sandbox may not have ffmpeg
im = Image.open(png).convert("RGB")
if a.shape == "circle":
    s = min(im.size); im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2)).resize((600, 600))
else:
    h = int(im.width * 1.25); top = max(0, (im.height - h) // 2)
    im = im.crop((0, top, im.width, top + min(h, im.height))).resize((1080, 1350))
im.save(png.with_suffix(".jpg"), quality=90)
png.unlink()
print(png.with_suffix(".jpg"))
