# R45S Facebook first-visible downward click fix

## Problem
R45R kept the downward-only frontier but still batch-clicked many collected expansion candidates in one viewport. On live Facebook this could skip newly exposed `View hidden comments`, `View hidden replies`, and `View all N replies` controls because the DOM mutates after each click.

## Fix
R45S changes the visible-page expansion loop to strict first-visible order:

1. Find the first visible expansion control in the current viewport.
2. Click exactly that one control.
3. Wait briefly and rescan the same viewport.
4. Repeat until no visible expansion controls remain in the current area.
5. Only then scroll downward.
6. Do not perform a global scroll-back-to-top rescan.
7. Do not start the replied-bucket follow-up while the main downward expansion still reports visible unresolved controls, incomplete progress, or timeout.

## Safety
The change continues to use only visible page controls in the operator-controlled browser session. It does not use hidden Facebook APIs, Graph endpoints, cookie/token extraction, browser-profile parsing, WebView2 storage inspection, or login automation.
