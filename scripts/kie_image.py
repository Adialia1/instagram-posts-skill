#!/usr/bin/env python3
"""Generate an image with GPT Image 2 through kie.ai, save it locally, and host files for Instagram.

    kie_image.py "prompt ..." --aspect 3:4 --out art/cover.png
    kie_image.py "prompt ..." --ref style.png --out art/cover.png

Used two ways by this skill:
- art.py calls it to paint a slide's picture (never text: slides.py typesets every word).
- publish.py / ig_workbench.py call upload() to put a rendered JPEG at a public URL that
  Instagram can fetch. kie.ai deletes uploads after 24 h, long enough for Instagram.

Stdlib only, so it runs under any python3 without a venv.

The key is read from $KIE_API_KEY or ~/.config/kie/api_key (chmod 600, outside the repo).
Never pass it on the command line: argv is visible in `ps`.

The API (docs.kie.ai):
  POST https://api.kie.ai/api/v1/jobs/createTask
       {"model": "gpt-image-2-text-to-image" | "gpt-image-2-image-to-image",
        "input": {"prompt", "aspect_ratio", "resolution", "input_urls"?}}
  GET  https://api.kie.ai/api/v1/jobs/recordInfo?taskId=...
       data.state in waiting|queuing|generating|success|fail,
       data.resultJson is a JSON *string* holding {"resultUrls": [...]}
  Local files go through the upload service first
  (POST https://kieai.redpandaai.co/api/file-stream-upload).
"""
import argparse
import json
import mimetypes
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
import uuid

API = "https://api.kie.ai/api/v1"
UPLOAD = "https://kieai.redpandaai.co/api/file-stream-upload"
KEY_FILE = pathlib.Path.home() / ".config/kie/api_key"

# GPT Image 2's ratios as documented. In practice kie.ai rejected 4:5, so art.py asks for
# 3:4 and crops to Instagram's 4:5 itself.
ASPECTS = ["1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5", "16:9", "9:16",
           "2:1", "1:2", "3:1", "1:3", "21:9", "9:21"]


def api_key() -> str:
    key = os.environ.get("KIE_API_KEY") or (
        KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")
    if not key:
        sys.exit(f"no kie.ai key: set KIE_API_KEY or put it in {KEY_FILE} (chmod 600)")
    return key


def request(method: str, url: str, key: str, body: bytes | None = None,
            ctype: str = "application/json") -> dict:
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"Bearer {key}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url} -> HTTP {e.code}: {e.read()[:400]!r}")
    # kie.ai answers HTTP 200 with an error code in the body, so the envelope
    # has to be checked as well as the status line.
    if out.get("code") != 200:
        sys.exit(f"{method} {url} -> {out.get('code')}: {out.get('msg')}")
    return out["data"]


def upload(path: pathlib.Path, key: str) -> str:
    """Upload a local file; returns a public URL (deleted by kie.ai after 24 h)."""
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts = []
    for name, value in (("uploadPath", "instagram-posts"), ("fileName", path.name)):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; "
                     f'name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                 f'filename="{path.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode())
    parts.append(path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    data = request("POST", UPLOAD, key, b"".join(parts),
                   f"multipart/form-data; boundary={boundary}")
    return data["downloadUrl"]


def generate(prompt: str, aspect: str, resolution: str, refs: list[str],
             key: str, timeout_s: int = 600) -> list[str]:
    model = "gpt-image-2-image-to-image" if refs else "gpt-image-2-text-to-image"
    inp = {"prompt": prompt, "aspect_ratio": aspect, "resolution": resolution}
    if refs:
        inp["input_urls"] = refs
    task = request("POST", f"{API}/jobs/createTask", key,
                   json.dumps({"model": model, "input": inp}).encode())["taskId"]
    print(f"task {task} ({model}, {aspect}, {resolution})", file=sys.stderr)

    # Poll with the request itself as the delay: no sleep dependency, and the
    # API is cheap to ask. GPT Image 2 took 40-120 s per image in practice.
    deadline = time.time() + timeout_s
    state = ""
    while time.time() < deadline:
        d = request("GET", f"{API}/jobs/recordInfo?taskId={task}", key)
        if d["state"] != state:
            state = d["state"]
            print(f"  {state}", file=sys.stderr)
        if state == "success":
            return json.loads(d["resultJson"])["resultUrls"]
        if state == "fail":
            sys.exit(f"task {task} failed: {d.get('failCode')} {d.get('failMsg')}")
        time.sleep(4)
    sys.exit(f"task {task} still {state} after {timeout_s}s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prompt", help="the prompt, or @file.txt to read it from a file")
    ap.add_argument("--out", type=pathlib.Path, required=True,
                    help="output path; a second result gets -2 appended")
    ap.add_argument("--aspect", default="9:16", choices=ASPECTS)
    ap.add_argument("--resolution", default="2K", choices=["1K", "2K", "4K"])
    ap.add_argument("--ref", action="append", default=[],
                    help="reference image: local path (uploaded) or URL; repeatable, max 16")
    args = ap.parse_args()

    prompt = args.prompt
    if prompt.startswith("@"):
        prompt = pathlib.Path(prompt[1:]).read_text(encoding="utf-8")
    key = api_key()
    refs = []
    for r in args.ref:
        refs.append(r if r.startswith("http") else upload(pathlib.Path(r), key))

    urls = generate(prompt, args.aspect, args.resolution, refs, key)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(urls):
        dest = args.out if i == 0 else args.out.with_stem(f"{args.out.stem}-{i + 1}")
        with urllib.request.urlopen(url, timeout=120) as r:
            dest.write_bytes(r.read())
        # Keep the prompt beside the image: a picture nobody can regenerate is a
        # picture nobody can adjust.
        dest.with_suffix(".prompt.txt").write_text(prompt, encoding="utf-8")
        print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
