"""Who is <name>@archon.social? Everything here reads public data: no wallet, no keys.

Three independent sources, so the answer can be cross-checked:
  1. The name service (Herald) on the name's domain: name -> DID.
  2. A DID resolver that is not the name service: DID -> DID document.
  3. The domain's LNURL-pay endpoint: name -> a Lightning pay request.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

#: Domains this agent will look names up on. A fixed list: the agent fetches
#: URLs built from what a caller typed, so the host is never the caller's choice.
DOMAINS = tuple(d.strip().lower() for d in os.environ.get("NAME_DOMAINS", "archon.social").split(",") if d.strip())
#: Any resolver that speaks the Universal Resolver HTTP API.
RESOLVER = os.environ.get("DID_RESOLVER_URL", "https://dev.uniresolver.io/1.0/identifiers/")
NAME = re.compile(r"(?<![\w.@-])([a-z0-9][a-z0-9_-]{0,31})@([a-z0-9.-]+\.[a-z]{2,})(?![\w-])", re.I)
DID_CID = re.compile(r"^did:cid:[a-z0-9]{20,120}$")


def find_name(text: str) -> tuple[str, str] | None:
    """The first name@domain in the text, lower-cased, if its domain is one we serve."""
    for m in NAME.finditer(text or ""):
        name, domain = m.group(1).lower(), m.group(2).lower()
        if domain in DOMAINS:
            return name, domain
    return None


async def _get(client: httpx.AsyncClient, url: str, accept: str = "application/json") -> tuple[int, Any]:
    try:
        r = await client.get(url, headers={"accept": accept})
    except httpx.HTTPError as e:
        return 0, str(e)
    if len(r.content) > 256_000:
        return r.status_code, "response too large"
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, None


async def who_is(name: str, domain: str) -> dict[str, Any]:
    """Look the name up, resolve its DID elsewhere, and check its Lightning address."""
    out: dict[str, Any] = {"name": f"{name}@{domain}", "found": False, "checks": [], "verify": {}}
    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        # 1. name -> DID, from the domain that owns the name.
        names_url = f"https://{domain}/.well-known/names/{name}"
        out["verify"]["name"] = names_url
        status, body = await _get(client, names_url)
        did = body.get("did") if isinstance(body, dict) else None
        if status != 200 or not isinstance(did, str) or not DID_CID.match(did):
            out["reason"] = "name not found" if status in (200, 404) else f"the name service answered {status or body}"
            return out
        out.update(found=True, did=did)

        # 2. DID -> document, from a resolver that is not the name service.
        resolve_url = f"{RESOLVER}{did}"
        out["verify"]["did"] = resolve_url
        # Ask for the resolution result, which carries the metadata; a resolver may answer the bare document instead.
        status, res = await _get(client, resolve_url, 'application/ld+json;profile="https://w3id.org/did-resolution", application/json;q=0.9')
        res = res if isinstance(res, dict) else {}
        doc = res.get("didDocument") if "didDocument" in res else (res if "id" in res else None)
        meta = res.get("didDocumentMetadata") or {}
        if status != 200 or not isinstance(doc, dict):
            out["checks"].append({"check": "DID resolves", "ok": False, "detail": f"resolver answered {status or res}"})
        else:
            ok = doc.get("id") == did and not meta.get("deactivated")
            out["checks"].append({"check": "DID resolves", "ok": ok,
                                  "detail": "deactivated" if meta.get("deactivated") else
                                  (f"version {meta['versionSequence']}, updated {meta.get('updated', '?')}" if meta.get("versionSequence") else "the document's id is this DID")})
            out["keys"] = [{"id": "#" + str(vm.get("id", "")).split("#")[-1], "type": vm.get("type"),
                            "curve": (vm.get("publicKeyJwk") or {}).get("crv")} for vm in doc.get("verificationMethod", []) if isinstance(vm, dict)]
            services = [s for s in doc.get("service", []) if isinstance(s, dict)]
            out["services"] = [{"id": "#" + str(s.get("id", "")).split("#")[-1], "type": s.get("type"),
                                "endpoint": s["serviceEndpoint"].get("uri") if isinstance(s.get("serviceEndpoint"), dict) else s.get("serviceEndpoint")} for s in services]

        # 3. A Lightning address is name@domain; its pay request is at a well-known URL.
        ln_url = f"https://{domain}/.well-known/lnurlp/{name}"
        out["verify"]["lightning"] = ln_url
        status, pay = await _get(client, ln_url)
        if status == 200 and isinstance(pay, dict) and pay.get("tag") == "payRequest":
            try:
                ident = dict((k, v) for k, v in json.loads(pay.get("metadata", "[]"))).get("text/identifier")
            except (ValueError, TypeError):
                ident = None
            out["lightning"] = {"address": f"{name}@{domain}", "min_msat": pay.get("minSendable"), "max_msat": pay.get("maxSendable"),
                                "names_itself": ident}
            out["checks"].append({"check": "Lightning address answers", "ok": True,
                                  "detail": "the pay request names " + (ident or "nobody")})
            out["checks"].append({"check": "pay request names the same identity", "ok": ident == f"{name}@{domain}", "detail": ident or "no identifier"})
        else:
            out["checks"].append({"check": "Lightning address answers", "ok": False, "detail": f"no pay request ({status})"})
    return out


def describe(r: dict[str, Any]) -> str:
    """The answer as text a person, or a model, can read and check."""
    if not r["found"]:
        return f"I could not find {r['name']}: {r.get('reason')}.\nCheck it yourself: {r['verify']['name']}"
    lines = [f"{r['name']} is {r['did']}", ""]
    for c in r["checks"]:
        lines.append(f"  [{'ok' if c['ok'] else 'FAILED'}] {c['check']}: {c['detail']}")
    if r.get("keys"):
        lines += ["", "Keys in its DID document: " + ", ".join(f"{k['id']} ({k['curve'] or k['type']})" for k in r["keys"])]
    if r.get("services"):
        lines.append("Services it publishes: " + ", ".join(f"{s['type']} at {s['endpoint']}" for s in r["services"]))
    if r.get("lightning"):
        ln = r["lightning"]
        lines.append(f"Lightning address: {ln['address']} ({(ln['min_msat'] or 0) // 1000} to {(ln['max_msat'] or 0) // 1000} sats)")
    lines += ["", "Do not take my word for it. Each answer came from a public URL you can fetch yourself:",
              f"  the name:      {r['verify']['name']}", f"  the DID:       {r['verify']['did']}", f"  the Lightning: {r['verify']['lightning']}",
              "The first and third are served by the name's own domain. The second is a resolver that has nothing to do with it."]
    return "\n".join(lines)
