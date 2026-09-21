# R45AC Facebook ordered read-only probe

The video showed the runner no longer behaving as a strict top-to-bottom operator pass. The likely cause was the R45AB probe itself: while discovering visible expansion controls it called `scrollIntoView({block: 'center'})` for edge candidates. That changed the scroll position during candidate discovery and could make the next click appear out of order.

R45AC changes the live pass:

- the probe is read-only;
- it does not call `scrollIntoView` while finding candidates;
- it only clicks controls already inside a safe visible work band;
- it sorts those controls by screen `top` then `left`;
- if no safe-band control is visible, the normal scroll step moves the dialog down;
- dialog scrolling is clamped to small increments so newly inserted controls are less likely to be jumped over;
- the pass remains locked to the Facebook comments dialog from R45AB.

Safety remains unchanged: visible page clicks only; no hidden Facebook APIs; no cookies/tokens/profile parsing; no WebView2 storage inspection; no login automation.
