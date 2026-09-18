# R43U Universal Social Account Ledger Contract Baseline

Status: pending local validation before commit.

## Purpose

R43U freezes the R43T/R43A Twitter/X account ledger method as a platform-neutral contract before Bluesky is added.

The reusable method is:

```text
visible browser/session capture
-> platform adapter normalizes visible records
-> media observations bind by safe identifiers / canonical URLs / DOM proximity
-> unbound account-level media candidates are preserved without fake binding
-> account/date/post/media/screenshot receipt ledger is written locally
```

## Boundary

R43U does not add live Bluesky capture yet. It does not start browsers, fetch hidden APIs, read cookies/tokens, perform login automation, bypass challenges, or download remote media.

## Baseline preserved

Twitter/X R43A/R43T/R43R are not replaced. R43U adds a universal ledger writer/contract and fixtures that prove the same account/date/post/media shape can represent both Twitter/X-like and Bluesky-like records.

## Bluesky preparation

Bluesky-specific identifiers remain nested under `platform_specific.bluesky`:

```json
{
  "did": "did:plc:...",
  "at_uri": "at://did:plc:.../app.bsky.feed.post/<rkey>",
  "cid": "...",
  "rkey": "...",
  "app_bsky_url": "https://bsky.app/profile/<handle>/post/<rkey>",
  "embed_type": "app.bsky.embed.images"
}
```

R43V can then add the real Bluesky visible-session adapter against this contract rather than inventing a separate ledger.
