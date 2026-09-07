# R42CQ process structure

R42CQ changes the archive.ph source row from a passive probe into an interaction-resume material worker.

Production path:

```text
Source URLs / TXT batch
→ archive.ph source row
→ GO / Webpage
→ native WebView2 visible interaction/material bridge
→ ACCESS_CHAIN_CONTINUING while challenge/intermediate page is visible
→ MATERIAL_LOAD_RUNNING after the page changes
→ article_text.txt/archive_page.html written when material appears
→ source-role judgement consumes source 03 material
```

Key behaviour:

- `intermediate` / `access_chain_continuing` is not terminal.
- Generic Playwright is not used as the archive access path after the native archive chain starts.
- The archive source candidate stays active until success or `access_chain_wait_expired`.
- The helper polls the visible WebView2 document and resumes automatically when article-like material appears.

This patch does not auto-solve third-party CAPTCHA widgets. It keeps the app-owned browser session alive and resumes extraction after the page itself becomes accessible.
