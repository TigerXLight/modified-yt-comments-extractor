# R45X Facebook expand-comments-only pass

R45X changes the Facebook live visual runner so expansion is treated as an explicit comment expansion pass rather than a broad page/candidate scan.

Rules:

- Click only explicit visible expansion controls: `View all N replies`, `View N replies`, `View hidden replies`, `View hidden comments`, `View more/previous replies`, and `Name replied · N replies`.
- Do not inspect/click broad comment containers, feed cards, comment composer controls, camera/upload/GIF/sticker controls, reactions, Like, Reply, Share, or Send.
- Click the next visible expansion text anchor, wait, rescan the same local area, and continue downward only when no explicit expansion text remains visible in that local area.
- Keep R45U target-page guard and R45W file-chooser guard.

This remains visible-page/operator-controlled only and does not use hidden Facebook APIs, cookies, tokens, browser-profile parsing, WebView2 storage inspection, or login automation.
