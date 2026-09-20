# R45N Facebook replied-reply-bucket expansion — 2026-09-20

## Problem

A live Facebook run expanded ordinary controls (`View all ... replies`, `View hidden comments`, `View hidden replies`) but still left collapsed reply-bucket labels such as:

```text
Fahad Malik replied · 14 replies
```

These labels are visible Facebook page controls, but they do not start with the older R45H patterns (`View all`, `View hidden`, `View 1 reply`).

## Fix

R45N keeps the existing R45H/R45J framework and adds a post-R45H visible-page follow-up pass: find `Name replied · N replies`, click those visible labels/buttons, then rerun the normal bounded expansion for any controls exposed by those buckets.

## Safety

No hidden Facebook APIs, Graph endpoints, cookies/tokens, WebView2 storage, browser-profile file parsing/copying, login automation, or remote media downloads are used.

## Useful run note

To avoid starting on `about:blank`, pass `--target-url` and omit `--manual-current-page`. Keep `--pre-expand-pause` so the operator can confirm that Facebook loaded correctly before expansion starts.
