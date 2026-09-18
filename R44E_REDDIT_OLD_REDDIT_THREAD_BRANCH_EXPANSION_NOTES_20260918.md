# R44E Reddit old Reddit thread branch expansion

R44E adds a Reddit thread-capture layer above R44D.

## Why this exists

For Reddit threads, the current Reddit interface can require multiple branch/comment pages before the visible comment tree is complete. Old/en Reddit can expose a much larger thread view with `sort=old`, `screen_view_count=1`, and `limit=500`, so R44E makes old/en Reddit the preferred first pass for Reddit thread captures.

This is Reddit-specific. It does not imply that old Twitter/X is suitable, because old Twitter/X may require a logged-in account.

## Default test thread

- Current Reddit thread: `https://www.reddit.com/r/EdSheeran/comments/1whbgzk/`
- Old Reddit preferred thread: `https://en.reddit.com/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/?sort=old&screen_view_count=1&limit=500&ext-referrer=DIRECT`

## Branch-page handling

R44E accepts explicit branch/comment URLs such as:

`https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/?force-legacy-sct=1`

It normalizes those to legacy/en Reddit URLs and preserves `force-legacy-sct=1`. Discovered `continue this thread` links are also converted into branch queue URLs.

## Downstream path

`R44E -> R44D -> R43U`

R44D still performs visible DOM extraction and media/comment/crosspost mapping. R43U still writes the account/date/post/media/screenshot ledger.

## Safety boundaries

R44E does not copy browser profiles, cookies, tokens, cache, local storage, Login Data, or WebView2 internals. It does not automate login, bypass challenges, use hidden Reddit APIs, or download remote media.
