"""Two public pages for people: what this agent is (GET /), and a demo (GET /demo?name=...).

The demo does not call the agent's own code. It sends the question to an agent gateway's access
point, DEMO_ACCESS_POINT, the way any A2A client would, and shows what came back. The gateway
holds the agent's key, so this page holds none.
"""
from __future__ import annotations

import html
import os
import time
from uuid import uuid4

import httpx
from starlette.requests import Request
from starlette.responses import HTMLResponse

from .lookup import DOMAINS, find_name

ACCESS_POINT = os.environ.get("DEMO_ACCESS_POINT", "").rstrip("/")
REPO = "https://github.com/Flaxscrip/archon-name-check"
EXAMPLE = f"genitrix@{DOMAINS[0]}"
#: At most this many gateway calls a minute from this page, all visitors together.
LIMIT_PER_MINUTE = 30
_calls: list[float] = []

STYLE = """
:root{--bg:#f7f6f2;--card:#fff;--ink:#1c1b19;--muted:#6b6862;--line:#e3e0d8;--ok:#1f7a4d;--bad:#b3261e;--accent:#2f5bd0}
@media (prefers-color-scheme:dark){:root{--bg:#161512;--card:#201f1b;--ink:#eceae4;--muted:#a09c93;--line:#34322c;--ok:#5fc48e;--bad:#f2867d;--accent:#8fb0ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:760px;margin:0 auto;padding:32px 16px 64px}h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.05rem;margin:28px 0 8px}
p{margin:8px 0}.muted{color:var(--muted)}a{color:var(--accent)}code,.mono{font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:12px 0}
form{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}input{flex:1 1 240px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
button{padding:10px 16px;border:0;border-radius:8px;background:var(--accent);color:#fff;font:inherit;cursor:pointer}
ul{padding-left:20px;margin:8px 0}li{margin:4px 0}.ok{color:var(--ok);font-weight:600}.bad{color:var(--bad);font-weight:600}
.path{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:.9rem}.path span{border:1px solid var(--line);border-radius:999px;padding:3px 10px;background:var(--card)}
"""


def _page(title: str, body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{STYLE}</style><main>{body}</main></html>",
        status_code=status, headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"})


def _form(value: str = "") -> str:
    return (f"<form method='get' action='/demo'><input name='name' value='{html.escape(value, quote=True)}' "
            f"placeholder='{html.escape(EXAMPLE)}' maxlength='80' aria-label='Name'><button>Who is it?</button></form>")


async def landing(request: Request) -> HTMLResponse:
    e = html.escape
    return _page("Archon name check", f"""
<h1>Archon name check</h1>
<p class="muted">An A2A agent with one skill: say who is behind a name like <code>{e(EXAMPLE)}</code>.</p>
{_form()}
<div class="card">
<p>Give it a name on an <a href="https://archetech.com/archon/">Archon</a> name service. It answers with the decentralised identifier (DID) behind the name, the keys and services that DID publishes, and its Lightning address, each with a public link to check the answer without the agent.</p>
<p>It reads public data only, and holds no wallet and no keys.</p>
</div>
<h2>For agents</h2>
<ul>
<li><a href="/.well-known/agent-card.json">The agent card</a>, which is public.</li>
<li>The agent itself answers only a gateway that holds its key, so calls go through an agent gateway surface.</li>
<li><a href="{REPO}/blob/main/recipe/who-is-it.md">The recipe</a>: put your own gateway in front of it, ask, and verify.</li>
<li><a href="{REPO}">The code</a> (MIT).</li>
</ul>""")


async def demo(request: Request) -> HTMLResponse:
    e = html.escape
    asked = request.query_params.get("name", "").strip()[:80]
    head = "<p><a href='/'>Archon name check</a></p><h1>Who is it?</h1>"
    if not asked:
        return _page("Who is it?", head + _form())
    found = find_name(asked)
    if not found:
        return _page("Who is it?", head + _form(asked) + f"<div class='card'><span class='bad'>Not a name I know.</span> Use the form <code>name@{e(DOMAINS[0])}</code>.</div>", 400)
    name = f"{found[0]}@{found[1]}"
    if not ACCESS_POINT:
        return _page("Who is it?", head + _form(name) + "<div class='card'>This demo is not connected to a gateway (DEMO_ACCESS_POINT is not set).</div>", 503)
    now = time.monotonic()
    _calls[:] = [t for t in _calls if now - t < 60]
    if len(_calls) >= LIMIT_PER_MINUTE:
        return _page("Who is it?", head + _form(name) + "<div class='card'>Too many questions this minute. Try again shortly.</div>", 429)
    _calls.append(now)

    # The same request any A2A client sends. No key: the gateway adds the agent's.
    body = {"jsonrpc": "2.0", "id": 1, "method": "message/send", "params": {"message": {
        "role": "user", "kind": "message", "messageId": uuid4().hex, "parts": [{"kind": "text", "text": f"Who is {name}?"}]}}}
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            res = await client.post(ACCESS_POINT, json=body)
        result = res.json().get("result") if res.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        res, result = None, None
    ms = int((time.monotonic() - started) * 1000)
    gateway = httpx.URL(ACCESS_POINT).host
    path = (f"<div class='path'><span>your browser</span>→<span>this page</span>→<span>gateway {e(gateway)}</span>→"
            f"<span>the agent</span><span class='muted'>{ms} ms</span></div>")
    if not result:
        why = f"the gateway answered {res.status_code}" if res is not None else "the gateway could not be reached"
        return _page("Who is it?", head + _form(name) + path + f"<div class='card'><span class='bad'>No answer:</span> {e(why)}.</div>", 502)

    data = next((p.get("data") for a in result.get("artifacts") or [] for p in a.get("parts") or [] if p.get("kind") == "data"), None)
    text = "".join(p.get("text", "") for p in ((result.get("status") or {}).get("message") or {}).get("parts") or [] if p.get("kind") == "text")
    out = [head, _form(name), path]
    if not isinstance(data, dict):
        out.append(f"<div class='card'><pre class='mono' style='white-space:pre-wrap;margin:0'>{e(text)}</pre></div>")
    elif not data.get("found"):
        link = (data.get("verify") or {}).get("name", "")
        out.append(f"<div class='card'><span class='bad'>Not found.</span> No name <code>{e(name)}</code> is registered.<br><a href='{e(link, quote=True)}'>Check it yourself</a></div>")
    else:
        verify = data.get("verify") or {}
        out.append(f"<div class='card'><div class='muted'>{e(name)} is</div><div class='mono' style='font-size:15px'>{e(str(data.get('did')))}</div></div>")
        out.append("<h2>What the agent checked</h2><ul>" + "".join(
            f"<li><span class='{'ok' if c.get('ok') else 'bad'}'>{'ok' if c.get('ok') else 'failed'}</span> {e(str(c.get('check')))}: {e(str(c.get('detail')))}</li>"
            for c in data.get("checks") or []) + "</ul>")
        if data.get("keys"):
            out.append("<h2>Keys in its DID document</h2><ul>" + "".join(
                f"<li><code>{e(str(k.get('id')))}</code> {e(str(k.get('curve') or k.get('type')))}</li>" for k in data["keys"]) + "</ul>")
        if data.get("services"):
            out.append("<h2>Services it publishes</h2><ul>" + "".join(
                f"<li>{e(str(s.get('type')))} at <code>{e(str(s.get('endpoint')))}</code></li>" for s in data["services"]) + "</ul>")
        if data.get("lightning"):
            out.append(f"<h2>Lightning address</h2><p><code>{e(str(data['lightning'].get('address')))}</code></p>")
        links = [("the name, at the name service", verify.get("name"))]
        links += [("the DID, at a public resolver", u) for u in (verify.get("did") or [])]
        links += [("the Lightning pay request", verify.get("lightning"))]
        out.append("<h2>Do not take its word for it</h2><p class='muted'>Each answer came from a public address. None needs the agent, the gateway or a key.</p><ul>" + "".join(
            f"<li>{e(label)}: <a href='{e(str(u), quote=True)}' rel='noreferrer'>{e(str(u))}</a></li>" for label, u in links if u) + "</ul>")
    out.append(f"<p class='muted'>Task state: {e(str((result.get('status') or {}).get('state')))}. This page sent an ordinary A2A request with no key; the gateway added the agent's key. <a href='{REPO}/blob/main/recipe/who-is-it.md'>Do the same from your own gateway.</a></p>")
    return _page(f"Who is {name}?", "".join(out))
