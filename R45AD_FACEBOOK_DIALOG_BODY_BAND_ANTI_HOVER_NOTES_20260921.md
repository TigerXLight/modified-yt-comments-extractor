# R45AD Facebook dialog body band + anti-hover

The 04:36 video shows two remaining live-run problems:

1. The pointer rests on profile/name areas and opens Facebook profile hover cards.
   Those overlays can cover reply controls and make the run appear out of order.

2. The comments modal can disappear, after which the browser lands back on the
   ordinary facebook.com feed. The runner must stop at that point instead of
   continuing to scroll or click the feed.

R45AD changes:

- expansion clicks are only allowed inside the comments dialog body band;
- the dialog header/close-button area is excluded;
- the sticky composer/footer area is excluded;
- after every click, the mouse is moved to a neutral left-gutter point to dismiss
  profile hover cards;
- before scrolling, after clicking, and after scrolling, the runner checks that
  the target comments dialog still exists;
- if the dialog is gone, it logs an R45AD stop marker and exits the expansion pass.

Safety remains unchanged: visible-page clicks only; no hidden Facebook APIs; no
cookie/token/profile parsing; no WebView2 storage inspection; no login automation.
