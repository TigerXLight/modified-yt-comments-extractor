# R42CR process structure — batch-safe archive access/material state

R42CR is not a CAPTCHA/check-box completion patch.

It changes archive.ph-style rows so the production Source URLs / GO / Webpage worker does not fall back to generic Playwright or reuse Metro/Wayback text when the archive page is gated.

## Production chain

```text
TXT / Source URLs batch
→ source rows created
→ GO / Webpage handles each row
→ archive.ph rows enter R42CR archive access/material chain
→ native WebView2 loads the source row in the app-owned session
→ ordinary non-gated pages may receive safe scroll nudges for lazy material
→ if article DOM/text appears, article_text.txt + archive_page.html are written
→ if the page remains an access gate, ACCESS_BLOCKED_CHALLENGE is recorded
→ source candidate is kept
→ batch continues
→ review/edit window displays the result/exception only
```

## States

- `success`: fresh archive article material was captured from the archive URL.
- `access_blocked_challenge`: the archive URL remained behind a visible access gate/challenge page.
- `material_unavailable_access_gate`: no usable article material appeared before the access/material wait ended.

## Non-goals

- No automatic CAPTCHA/check-box completion.
- No synthetic mouse-event bypass of access gates.
- No substitution of Metro or Wayback material as archive.ph proof.
- No generic Playwright fallback loop for archive.ph access-gate pages.

## Audit folder

R42CR writes archive attempts under:

```text
profile_media_live_captures\r42cr_archive_source_material
```

The verifier is:

```cmd
tools\webview2_source_role_editor_native\verify_r42cr_archive_material_audit.cmd
```
