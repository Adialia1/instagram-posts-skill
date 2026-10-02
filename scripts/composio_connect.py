#!/usr/bin/env python3
"""Instagram Graph API calls through Composio, from a laptop or a cloud run.

    from composio_connect import ig_call
    ig_call("GET", f"{uid}/media?fields=id,caption&limit=5")
    ig_call("POST", f"{uid}/media", {"image_url": "...", "caption": "..."})

    python3 composio_connect.py whoami [--save]     # your Instagram user id (+ write it to brand.json)
    python3 composio_connect.py GET "<path>"        # any call, for debugging

Two routes to the same connected Instagram account:
- Locally: the Composio CLI (`composio proxy`), after `composio login` + `composio link instagram`.
- Without the CLI: Composio's MCP endpoint (https://connect.composio.dev/mcp) with a consumer key
  in COMPOSIO_CONSUMER_API_KEY (a `ck_...` key from the Composio dashboard). That endpoint has no
  proxy tool of its own, so the request runs inside its COMPOSIO_REMOTE_WORKBENCH tool, whose
  preloaded `proxy_execute(method, endpoint, toolkit, body=...)` is the same proxy the CLI uses.
  The `ck_` key is for MCP only; the REST API rejects it.
  (A cloud routine with the Composio MCP *connector* attached uses ig_workbench.py instead.)

Composio's Instagram login is "Instagram API with Instagram Login": the host is graph.instagram.com
(graph.facebook.com answers error 190). A JSON body sends a raw '#' in captions.
"""
import json, os, pathlib, subprocess, sys, tempfile, time, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import BRAND_FILE, IG_API, composio_cli

MCP = "https://connect.composio.dev/mcp"


def _mcp(method, params, key):
    body = json.dumps({"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": method, "params": params}).encode()
    req = urllib.request.Request(MCP, data=body, headers={"x-consumer-api-key": key, "content-type": "application/json",
                                                          "accept": "application/json, text/event-stream"})
    raw = urllib.request.urlopen(req, timeout=200).read().decode()
    for line in raw.splitlines():               # a server-sent-events stream: take the JSON-RPC message
        if line.startswith("data:"):
            msg = json.loads(line[5:])
            if "error" in msg: raise SystemExit(f"composio mcp: {msg['error']}")
            return msg["result"]
    raise SystemExit(f"composio mcp: no message in response: {raw[:300]}")


def _via_connect(method, path, body, key):
    code = ("import json\n"
            f"res, err = proxy_execute({method!r}, {IG_API + '/' + path!r}, 'instagram', body={body!r})\n"
            "print('@@RESULT@@' + json.dumps({'res': res, 'err': err}, ensure_ascii=False, default=str))")
    out = _mcp("tools/call", {"name": "COMPOSIO_REMOTE_WORKBENCH",
                              "arguments": {"code_to_execute": code, "thought": f"Instagram {method} {path.split('?')[0]}",
                                            "current_step": "INSTAGRAM_API"}}, key)
    # The tool's text is itself JSON: {"data": {"stdout": "...@@RESULT@@{json}\n", ...}, "successful": ...}
    text = "".join(c.get("text", "") for c in out.get("content", []) if c.get("type") == "text")
    try:
        stdout = json.loads(text)["data"]["stdout"]
    except Exception:
        raise SystemExit(f"composio workbench: unexpected output: {text[:400]}")
    marker = stdout.find("@@RESULT@@")
    if marker < 0: raise SystemExit(f"composio workbench: no result: {stdout[:400]}")
    payload = json.loads(stdout[marker + 10:].split("\n")[0])
    if payload.get("err"): return {"error": payload["err"]}
    return payload["res"]


def _via_cli(method, path, body):
    cmd = [composio_cli(), "proxy", f"{IG_API}/{path}", "--toolkit", "instagram", "-X", method]
    if body is not None:
        f = pathlib.Path(tempfile.mkdtemp()) / "b.json"; f.write_text(json.dumps(body, ensure_ascii=False))
        cmd += ["-H", "content-type: application/json", "-d", f"@{f}"]
    r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"composio proxy: no JSON back (is Instagram linked? `composio link instagram`)\n{r.stdout[:300]}{r.stderr[:300]}")


def ig_call(method, path, body=None, raise_on_error=True):
    key = os.environ.get("COMPOSIO_CONSUMER_API_KEY")
    j = _via_connect(method, path, body, key) if key else _via_cli(method, path, body)
    if raise_on_error and isinstance(j, dict) and "error" in j:
        raise SystemExit(f"{method} {path}: {j['error']}")
    return j


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "whoami":
        me = ig_call("GET", "me?fields=user_id,username")
        print(json.dumps(me, ensure_ascii=False))
        if "--save" in sys.argv:
            b = json.loads(BRAND_FILE.read_text())
            b["instagram_user_id"] = str(me.get("user_id") or me["id"])
            BRAND_FILE.write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n")
            print(f"saved instagram_user_id to {BRAND_FILE}")
    elif len(sys.argv) > 2:
        print(json.dumps(ig_call(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else None), ensure_ascii=False)[:2000])
    else:
        sys.exit(__doc__)
