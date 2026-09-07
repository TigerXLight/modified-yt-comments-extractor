# R42BM native WebView2 source-role editor structure

R42BM keeps the R42BI database-maintenance checkpoint and adds in-window source URL navigation.

## Runtime speed path

- The Python/Tk app starts one warm native WebView2 helper on `about:blank`.
- Opening the source-role editor sends a small command JSON to the warm helper.
- The helper navigates the existing WebView2 control to the selected source URL.
- First paint still comes from `selected_link_source_role_overlay.json`; SQLite is not in the first-paint path.
- Role clicks and Semantic/Media switching remain local DOM updates.

## New in-window source navigation

The overlay payload now carries `source_navigation_urls`, normally ordered as:

1. Original live source URL
2. Wayback Machine URL
3. archive.ph/archive.today/archive.is URL

The native toolbar shows a compact `1/3 Original`, `2/3 Wayback`, etc. control with previous/next buttons.

Navigation uses the same already-open WebView2 control and the same loaded role payload. It does not create a second Python callback, second helper command, or second editor process.

## Database structure

- `selected_link_source_role_overlay.json` remains the fast first-paint source.
- `selected_link_source_role_overlay_changes.jsonl` remains the append-only audit trail.
- `selected_link_source_role_roleplan.sqlite` stores compact current/history state.
- Maintenance/VACUUM is manual/off-path via `maintain_r42bm_source_role_db.cmd`.

## Important invariant

Do not move SQLite reads/writes, VACUUM, JSONL compaction, or archive lookup into the document-start paint path. The edit window should stay responsive even when database maintenance or full Metro page load is slow.

## R42BM source dropdown

The native toolbar now renders the source navigation list as a dropdown. Selecting Original, Wayback, or archive.ph navigates the existing warm WebView2 control with `location.assign`, so it does not issue a new Python/server command and does not alter the local role-click/toggle path.

## R42BM archive-safe toolbar dock

The native YTCE toolbar now auto-docks to the bottom for Wayback/archive URLs so it does not cover the archive service's own top banner/date controls. A small ⇧/⇩ button toggles top/bottom manually. Source URL navigation still happens inside the same warm WebView2 instance and does not issue a new server command per dropdown selection.


## R42BM toolbar safe-area update

R42BM keeps the source URL dropdown from R42BK/R42BL, but changes the toolbar layout policy.
The YTCE toolbar stays at the top by default and reserves page space using a CSS safe-area offset.
This prevents the editor toolbar from covering the top of live pages, Wayback's date/banner UI,
or other archive controls. The manual top/bottom toggle remains available, and bottom mode reserves
bottom space rather than covering article text.

The safe-area update is local DOM/CSS work only. It does not add a database dependency, does not add
new server commands for source navigation, and should preserve the instant role-click/mode-toggle path.
