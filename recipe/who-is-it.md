# Who is it? Check an agent's name before you trust it

> Draft for the Agent Lab catalogue, in the catalogue's own format.
> Status: run end to end on 17 Nov 2026, through an Affinidi Agent Gateway (v1.0.6) surface, with the
> Lab's *Hello, agent* command-line client. Every step below was done as written.

| | |
| --- | --- |
| **id** | `who-is-it` |
| **Summary** | Put your gateway in front of an agent that looks up a name such as `genitrix@archon.social`, then check every part of its answer yourself, without trusting the agent or the gateway. |
| **Difficulty** | Introductory |
| **Time** | 15 minutes |
| **Tags** | a2a, identity, did, did:cid, gateway, verification |
| **Needs** | Get an agent gateway; Hello, agent (for the command-line client) |
| **Target** | Archon name check, an A2A agent at `https://namecheck.archon.social` |
| **Provided** | The agent's API key. It goes into your gateway, never into your client. |

## What you will do

Ask an agent who is behind a name, then prove its answer without relying on it.

- **In your gateway dashboard**
  - Put your gateway in front of the name check agent, holding its key
- **On your machine**
  - Ask it who `genitrix@archon.social` is
  - Check its three answers yourself, each from a public address
  - Ask about a name that does not exist
- **Here, or through your agent**
  - Mark the recipe complete

In the other recipes, every identity was one your own gateway made up: a DID for a caller, for a
surface, for an agent. Those are useful inside your gateway and mean nothing outside it.

An agent that works across organisations needs a name that somebody else can check. This recipe uses
one kind: a name on a name service (`genitrix@archon.social`) that points at a DID
(`did:cid:…`), which anyone can resolve to the keys and services its owner published. The agent you
call only does the looking up. The point is that you do not have to believe it.

## Before you start

You need *Hello, agent* done, with the recipes repository cloned and its client working.

Read the agent's card. It is public and needs no key:

```
GET https://namecheck.archon.social/.well-known/agent-card.json   → 200
POST https://namecheck.archon.social/                             → 401
```

The card describes one skill, in prose: say who is behind a name. The 401 is expected: you called
without the key. Your gateway will supply it.

## 1. Put your gateway in front of it

Everything in this step is in your gateway dashboard.

1. Create a new A2A surface.
2. On it, set:
   - **Target**: `https://namecheck.archon.social`
   - **Target authentication**: an API key in the `x-api-key` header, with this key:

     ```
     {{API key}}
     ```
3. Make the access point public, save the surface, and copy its **access point**.

## 2. Ask who it is

1. In the *Hello, agent* client's `.env`, set `A2A_ACCESS_POINT` to your new access point.
2. Ask:

   ```
   ./run.sh -m "Who is genitrix@archon.social?"
   ```

The agent answers with a DID, three checks, the keys and services in the DID document, and a
Lightning address:

```
genitrix@archon.social is did:cid:bagaaieraxdxq4fm2kjh6yqjxjor3t2idczkmxd4v7in4u353fa6m6sms2pnq

  [ok] DID resolves: version 29, updated 2026-11-16T19:06:20Z
  [ok] Lightning address answers: the pay request names genitrix@archon.social
  [ok] pay request names the same identity: genitrix@archon.social
```

It ends with the address each answer came from. You use those next.

The client also prints a block headed **WHAT YOUR GATEWAY ADDED**, which says "Nothing". That block
belongs to *Hello, agent*, where the gateway signs a statement about the agent. This surface has no
Identity element, so there is nothing to show, and nothing is wrong.

## 3. Check it yourself

Do not take the agent's word for any of it. Open each address the reply gave you. None of them
needs the agent, your gateway or a key.

| What the agent said | Where to check it | Who serves that |
| --- | --- | --- |
| The name points at this DID | `https://archon.social/.well-known/names/genitrix` | The name service that owns the name |
| The DID resolves, with these keys and services | `https://uniresolver.io/#did:cid:…` | The DIF Universal Resolver, which has nothing to do with the name service or the agent |
| A Lightning address answers for the name | `https://archon.social/.well-known/lnurlp/genitrix` | The name service again |

Compare the DID in the first with the one you resolve in the second. They must be the same string.
In the resolved document, find the three keys the agent listed, and the `Lightning` and
`DIDCommMessaging` services.

What you have checked: a name, the identifier behind it, the keys its owner can sign with, and
where to pay or message them. Three parties answered, and they agree.

## 4. Ask about a name that does not exist

```
./run.sh -m "Who is nobody-at-all@archon.social?"
./run.sh -m "hello"
```

The first completes, and says the name was not found, with the address to confirm that. The second
does not complete: the state is `input-required`, because the agent needs a name before it can do
anything. Start the client without `-m` (`./run.sh`) to answer it in the same conversation.

## How you know you are done

- Through your access point, the agent tells you who `genitrix@archon.social` is.
- You opened the three addresses yourself, and the DID from the name service matches the DID you
  resolved.

When that is true, mark the recipe complete. Nothing checks it: the Lab takes your word.

## What just happened

Your gateway did one job, the one it did in *Hello, agent*: it held the agent's key.

The identity came from somewhere else. `genitrix@archon.social` is a name its owner registered. The
DID behind it was created by its owner, and no gateway, agent or Lab issued it. The document it
resolves to says which keys can sign for that identity and where it takes messages and payments.
Any resolver that knows the `did:cid` method gives the same document.

That is the difference from a DID your gateway makes for a caller. A gateway's DID says "my gateway
saw this caller". A DID like this one says "this is who I am", and stays the same at every gateway,
every agent and every organisation that looks it up.

## Try breaking it (optional)

- **Ask about a name on another domain**, such as `someone@example.com`. The agent asks which name
  you mean. It only looks names up on the domains it was set up for, so a caller cannot make it
  fetch an address of the caller's choosing.
- **Call the agent directly, without your gateway.** You get the 401 from *Before you start*. The
  key is in your gateway and nowhere else.
- **Resolve the DID on a second resolver**, `https://resolver.archon.technology/1.0/identifiers/did:cid:…`.
  The document is the same. Which resolver you ask does not change who the DID is.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| `503 This Access Point is not available` | The access point is closed. Make it public (step 1) |
| `401` from the agent | Target authentication is missing or the key is wrong. Check the secret and the header name `x-api-key` |
| `[FAILED] DID resolves: the resolver could not be reached` | The resolver was briefly unreachable. Ask again, and check the DID yourself at the address in the reply |
| The agent asks "Which name?" | Your message had no name on a domain it knows. Use the form `name@archon.social` |

## Where this goes next

This recipe checks who an agent is. Two more build on it, and are not written yet:

- **Where do I pay it?** Use the Lightning address from the answer to request an invoice, and check
  it names the same identity.
- **Give me a receipt.** Have the agent create an asset with its own DID and transfer it to yours.
