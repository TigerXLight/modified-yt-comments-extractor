# R45L Facebook Preserved Visual Comments Column Crop Notes — 2026-09-19

## Problem

After R45J fixed the blank white screenshot issue by avoiding clone-and-replace of `document.body`, the live preserved-visual route could still produce the wrong visual: it preserved the full original Facebook post modal/post/media surface instead of the manually expected comments-only column, like the Print Edit WE cropped view.

The operator expectation is:

- use the original Facebook-rendered page as the visual source;
- keep Facebook comment bubbles, avatars, nesting, reactions, and Like/Reply metadata;
- cut away the surrounding original post chrome/post media/header/composer surfaces;
- produce a cropped comments-column screenshot, not the full post modal.

## Change

R45L updates the R45J preserved visual cleanup route. It still works in place and still avoids body clone/replacement, but it now:

1. finds the first visible Facebook comment/reply anchor using visible text such as `Like Reply`, `View all replies`, `View more replies`, and hidden comment/reply controls;
2. marks visible elements above that first comment anchor with `data-r45j-pre-comment-hide="true"`;
3. keeps the selected Facebook-rendered comments root and adds `data-r45j-comment-column-crop="true"`;
4. adds a dedicated cropped root screenshot:
   `facebook_preserved_visual_comments_column.png`;
5. keeps the existing full-page and tile screenshots for audit/backup.

## Safety

No new scraping surface was added.

R45L does not use hidden Facebook APIs, Graph endpoints, cookies, tokens, WebView2 storage, browser profile file parsing/copying, login automation, or remote media downloads.

It only changes the post-expansion visible DOM cleanup and local screenshot capture behavior.

## Expected visual

The preferred output after R45L is `facebook_preserved_visual_comments_column.png`.

That image should resemble the operator's manual Print Edit WE crop: the original Facebook-rendered comment column, cut down from the full post/modal view, without the large top post/media surface.
