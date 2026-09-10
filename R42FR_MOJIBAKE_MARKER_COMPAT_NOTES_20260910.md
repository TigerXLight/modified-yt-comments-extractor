# R42FR mojibake marker compatibility

Restores/continues the R42FP/R42FQ test-file repair and updates stale mojibake string assertions in `main_source_resource_ui_test.py` to the current UTF-8 production labels.

Scope:
- test-only
- no production code changes
- no WebView2 build outputs
- no untracked audit/backup files

Reason:
The source-row/media-resource UI tests still expected mojibake forms such as `LIVE Ã¢â€“Â¶`, `Ã‚Â·`, `Ãƒâ€”`, and `Ã¢â‚¬â€`, while current runtime source uses proper UTF-8 glyphs such as `LIVE ▶`, `·`, `×`, and `—`.
