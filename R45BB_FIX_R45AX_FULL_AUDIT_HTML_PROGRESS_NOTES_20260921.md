# R45BB fix: full audit + HTML progress probe

This fixes the inspected R45AX/R45BA local files.

Findings from uploaded local files:
- R45BA correctly fixed the 720px outer-dialog false scroller issue.
- The current R45AX still accepts completion after a single downward pass: at bottom + no visible control in that viewport = PASS.
- That can miss controls above after newly inserted comments, for example later `View 1 reply` controls.
- Progress was only checked from visible text; the requested `N of M` gate can exist in live HTML/attributes and not in innerText.

R45BB changes:
- Completion now requires a full top-to-bottom zero-control audit pass. If any click happened during a pass, it restarts at top and audits again.
- Progress detection checks visible text, textContent, aria/title attributes, and stripped live HTML.
- Replied buckets are more flexible: `replied · 3 replies`, `replied 3 replies`, etc.
- Candidate detection now includes element-level labels as well as text nodes, for split labels.
- It writes `r45ax_live_before_flatten.html` and `r45ax_live_before_flatten_text.txt` before flattening for later inspection.
