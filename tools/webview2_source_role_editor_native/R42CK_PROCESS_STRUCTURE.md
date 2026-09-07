# R42CK Native WebView2 source-role editor

Purpose: correct the source-role model for TXT/link batches.

The dropdown/source navigation list is only an inspection surface. The app must keep every URL from the TXT/link input as a stable source candidate and the batch checker must judge the source role from the full loaded source material before the user optionally inspects it.

Correct model:

```text
TXT/link input
→ app creates one stable SourceCandidate per URL
→ app checks/accesses each candidate
→ app loads full source material where possible
→ app extracts article/source evidence
→ app assigns/proposes Primary/Secondary/Tertiary/Unknown
→ edit window is optional inspection/correction only
```

Archive/CAPTCHA/cookie/security pages are access state, not source-role state:

```text
03 | A | archive.ph/6mr3C | title | Archive
```

must remain candidate 03 even if the visible WebView temporarily shows:

```text
archive.ph/
archive.ph challenge/intermediate page
HTTP 429 page
security-check page
```

The transient visible page must not replace candidate 03, and candidate 03 must not be silently left for manual judgement. When full article/source markers become available, the batch source-role checker must resume automatically and judge candidate 03 from the loaded page material.

Expected dropdown for a three-link batch:

```text
01 | People shout "seagull eater"... | Metro
02 | W | People shout "seagull eater"... | Metro
03 | A | People shout "seagull eater"... | Archive
```

R42CK changes:
- Keeps archive.ph/archive.today rows as stable batch source candidates.
- Stops using “pending human verification” language for source-role state.
- Logs archive access interruptions as `native_access_chain_barrier`.
- Logs resumed content candidates as `native_access_chain_resume_candidate`.
- Keeps WebView below the native toolbar.
- Keeps the selected archive source sticky if the visible URL collapses to an archive root/intermediate page.
- Clarifies that edit window inspection is not required for all links in a TXT batch.

Final intent:

```text
Access-chain state may pause/retry loading.
Source-role judgement must still be automatic once full content is available.
```
