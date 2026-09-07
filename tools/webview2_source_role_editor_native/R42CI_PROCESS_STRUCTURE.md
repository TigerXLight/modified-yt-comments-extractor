# R42CI Native WebView2 source-role editor

Purpose: fix the remaining two-row dropdown problem by treating Human Action Queue/TXT input as source-navigation state, not just evidence/checkbox state.

Expected dropdown for a three-link human TXT batch:

```text
01 | People shout "seagull eater"... | Metro
02 | W | People shout "seagull eater"... | Metro
03 | A | People shout "seagull eater"... | Metro
```

Notes:
- archive.ph/archive.today rows are navigation-only human-chain peers until article markers pass.
- no CAPTCHA/challenge solving is automated.
- native toolbar still paints from the selected payload and keeps WebView below the native toolbar.

- Native local archive discovery also has a narrow ordinal sibling fallback for 01/02/03 human-chain capture folders.


R42CI compile fix:
- Fixes native_toolbar_ready debug nav_items logging to use NativeSourceNavItem.IndexLabel.
- No functional change to source-row collection logic from R42CH.
