# Archon name check

An [A2A](https://a2a-protocol.org) agent with one skill: **who is `name@archon.social`?**

Ask it about a name on an [Archon](https://archetech.com/archon/) name service and it answers with:

- the DID behind the name (`did:cid:…`),
- whether that DID resolves on an independent resolver, and the keys and services its document publishes,
- whether a Lightning address answers for the name, and whether the pay request names the same identity.

It reads public data only. It holds no wallet and no keys, and every answer comes with the URL to check it without the agent.

```
you   > Who is genitrix@archon.social?
agent > genitrix@archon.social is did:cid:bagaaiera…
          [ok] DID resolves: version 29, updated 2026-11-16T19:06:20Z
          [ok] Lightning address answers: the pay request names genitrix@archon.social
          [ok] pay request names the same identity: genitrix@archon.social
        …
```

The reply is text for a person and, as an artifact named `who-is`, the same facts as data for a caller that wants to act on them.

## Where the answers come from

| Fact | Source | Served by |
| --- | --- | --- |
| name → DID | `https://<domain>/.well-known/names/<name>` | The name's own domain (Herald) |
| DID → document | `<DID_RESOLVER_URL><did>`, the Universal Resolver HTTP API | A Universal Resolver, not the name service. The reply links two public ones to check against: the DIF Universal Resolver page at `uniresolver.io` and Archon.s `resolver.archon.technology` |
| Lightning address | `https://<domain>/.well-known/lnurlp/<name>` (LNURL-pay) | The name's own domain |

## Run it

Python 3.10 or newer.

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m name_check            # http://localhost:8090, card at /.well-known/agent-card.json
```

| Variable | Default | |
| --- | --- | --- |
| `PUBLIC_URL` | `http://localhost:<port>` | The address on the agent card |
| `HOST`, `PORT` | `127.0.0.1`, `8090` | Where it listens |
| `NAME_DOMAINS` | `archon.social` | Comma-separated domains whose names it will look up. Nothing else is ever fetched |
| `DID_RESOLVER_URL` | `https://resolver.archon.technology/1.0/identifiers/` | The resolver the agent asks. Any resolver that speaks the Universal Resolver API, private ones included |
| `DID_VERIFY_URL` | `https://uniresolver.io/#,https://resolver.archon.technology/1.0/identifiers/` | The public resolvers the reply points callers at to check the DID themselves, comma-separated |

A container: `docker build -t archon-name-check . && docker run -p 8090:8090 -e PUBLIC_URL=https://<host> archon-name-check`.

## Behind an agent gateway

The agent asks for no credential of its own. To put it behind an Affinidi Agent Gateway, create an A2A surface whose target is the agent's public HTTPS address, and call the surface's access point. On a public host, require a key in a header at the reverse proxy and give that key to the gateway as target authentication, so the gateway is the only way in.

## Not yet

- The agent does not sign its answers. Signing them with its own `did:cid` is the next step.
- It answers about a name. It does not yet take a DID and say which names point at it.
