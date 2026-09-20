# R45W — Facebook no-file-chooser expand guard

R45V correctly moved expansion clicks to Playwright mouse events, but live testing showed a new failure mode: a broad Facebook Comet container could put the computed click centre on the comment composer camera/upload control, opening the native Windows `Open` file dialog.

R45W keeps the same operator-requested rule:

```text
first visible expandable control
click it
rescan the same visible area
then continue downward only
```

But it tightens candidate selection:

- only intrinsically clickable controls are scanned (`role=button`, links, buttons, `tabindex=0`), not every `div`/`span`;
- click coordinates are anchored to the exact visible text for `View all N replies`, `View hidden replies`, `View hidden comments`, `Name replied · N replies`, or `See more`;
- comment composer/upload/photo/GIF/sticker/file-input surfaces are explicitly excluded;
- a Playwright `filechooser` event handler is registered as a secondary guard and logs `R45W_FILE_CHOOSER_BLOCKED` if such a surface is ever hit.

No hidden Facebook APIs, cookies/tokens, browser profile parsing, WebView2 storage inspection, or login automation are added.
