# R45AI legacy fast ordered 2026-09-19 runner

This keeps the old 2026-09-19 working legacy engine rather than the later
R45V-R45AF mouse/text-rect path.

Changes against R45AH:
- keeps the legacy page-side `el.click()` expander;
- clicks only controls already visible in the viewport;
- removes `scrollIntoView({block: "center"})` from the batch clicker;
- sorts visible expansion controls top-to-bottom first;
- increases visible click batch size;
- uses faster but still conservative click/scroll delays;
- reduces scrolls per round so it does not spend as long scanning empty areas.

This is intentionally a separate runner, not a replacement for the stable R45AH
legacy runner.

Safety:
- visible Facebook page expansion only
- no hidden Facebook APIs
- no cookies/tokens/profile parsing
- no WebView2 storage inspection
- no login automation
