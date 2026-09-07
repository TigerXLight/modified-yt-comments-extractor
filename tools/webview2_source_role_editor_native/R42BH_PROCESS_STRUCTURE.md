# R42BH native WebView2 source-role editor process/database checkpoint

R42BH keeps the R42BG/R42BF speed architecture: native WebView2 warm server for runtime speed, JSON payload for first paint, and SQLite as the durable sidecar.  The database is for clean structure, history, current state, and maintenance; it is intentionally not in the first-paint path.

## R42BH changes

- Debounces duplicate editor-open commands in Python before command files are written.
- Adds a server-side duplicate-command guard, so a double-fired edit button cannot create two near-identical navigations.
- Keeps command-file atomic writes from R42BB/R42BG.
- Keeps stale about:blank document-start-script cleanup from R42BG.
- Adds DB maintenance/pruning commands now, without deleting raw JSONL audit data.
- Adds archive tables for older DB rows:
  - `role_source_sessions_archive`
  - `role_plan_rows_archive`
  - `role_change_events_archive`
- Adds `db_maintenance_runs` so every DB maintenance run has an audit summary.
- Adds `maintain_r42bh_source_role_db.cmd`.

## Database policy

The database should not slow down the edit window:

1. First paint still reads `selected_link_source_role_overlay.json`.
2. SQLite sync runs as a background sidecar.
3. Raw JSONL stays append-only as the audit log.
4. Compact/current SQLite tables are used for inspection and future role decisions.
5. Maintenance is manual or scheduled outside the critical editor-open path.

## Hot/current DB tables

- `role_plan_current`: current 122-row plan for selected URL + mode + edit key.
- `role_latest`: latest compact role decision per selected URL + mode + edit key.
- `role_change_events`: compact useful change events, not raw click spam.

## Historical/archive tables

- `role_source_sessions` and `role_plan_rows` keep recent session history.
- `*_archive` tables keep old DB rows when maintenance prunes hot tables.
- Raw `selected_link_source_role_overlay_changes.jsonl` is untouched.

## Maintenance command

Run:

```cmd
cd /d "T:\References	o go\Media	ools\Modified YouTube comment extractor" && tools\webview2_source_role_editor_native\maintain_r42bh_source_role_db.cmd
```

Default policy:

- keep latest 25 payload sessions per URL in hot tables
- keep latest 5000 compact change events in hot table
- archive older DB rows before deleting from hot tables
- run WAL checkpoint, ANALYZE, PRAGMA optimize, and VACUUM

## Current process priority

Do not switch to HSQLDB, Outerbase, or database GUI repos for editor speed.  The speed-critical runtime remains WebView2 warm server.  The database work is about reliability, current state, history, pruning, and future review decisions.
