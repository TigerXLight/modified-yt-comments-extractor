# R44K Reddit R44I/R44J real capture reconciliation

R44K compares a successful R44I logged-in target-only Reddit capture against the R44J comment-tree extraction layer.

It is a local reconciliation layer only. It reads prior R44I evidence files and R44D/R43U receipts from `profile_media_live_captures`; it does not start a browser, access Reddit, read or copy browser profile internals, parse cookies/tokens, automate login, or download remote media.

## Purpose

The real EdSheeran capture produced 349 R44I/R44D ledger records from the old/en Reddit target page. The reference transcript says Reddit displayed 337 comments and represented 333 recoverable comment nodes. R44K records the differences between:

- R44I/R44D visible ledger records
- R44J parsed comment nodes
- reference recoverable comment nodes
- Reddit displayed comment counter

The important rule is that count differences are recorded and classified; missing comments are not invented.

## Large threads

For 1k+ Reddit-comment threads, old Reddit `limit=500` is not a completeness guarantee. R44K is designed to be run after each target-only or branch-page capture so a resumable queue can reconcile recovered comments page by page.
