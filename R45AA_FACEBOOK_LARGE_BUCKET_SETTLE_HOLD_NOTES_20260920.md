# R45AA Facebook large bucket settle hold

R45AA fixes the live-run regression where the runner clicked a large opener such as
`View all 302 replies`, saw the label disappear, and scrolled downward after about
two seconds before Facebook finished streaming the newly opened replies.

The pass remains expand-comments-only:
- click explicit visible expansion text only;
- do not click comments, feed cards, reactions, Like/Reply, composer, camera, GIF,
  sticker, upload, or file chooser controls;
- continue downward only after the current large bucket has had a real minimum
  settle window.

Safety:
- visible page clicks only;
- no hidden Facebook APIs;
- no cookies/tokens/profile parsing;
- no WebView2 storage inspection.
