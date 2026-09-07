# R42BF Source-Role Editor Structure / Process

R42BE proved the correct speed direction: keep the live browser runtime in a native WebView2 helper and keep the database outside the first-paint path.

## Runtime split

1. **Main Python/Tk app**
   - owns the review workflow and selected-source state
   - starts the warm native WebView2 helper early, on `about:blank`
   - writes the selected-source payload JSON when the editor is requested

2. **Selected-source payload JSON**
   - remains the fast, single payload for the browser
   - contains `rows_by_mode.semantic` and `rows_by_mode.media`
   - is small enough to inject at document-start

3. **Native WebView2 helper**
   - keeps one app-owned persistent WebView2 user-data folder
   - receives source open commands through the warm command directory
   - injects the top-frame-only role painter at document-start
   - paints from the prepared role plan, not by repeatedly rescanning the whole page
   - edits DOM colour immediately on click, then saves asynchronously

4. **SQLite sidecar / Review DB path**
   - stores durable source sessions, role-plan rows, compact change events, and latest role state
   - is useful for audit, history, queues, filtering, and later DB-driven review screens
   - must not block WebView2 startup, navigation, document-start injection, or first colour paint

## Performance checkpoint meanings

- `server_command_to_first_role_paint` is the important editor-open speed measurement after the warm helper is running.
- `navigation_completed` / full page load is less important because Metro keeps loading ads, trackers, and video scripts after the article is already usable.
- `role_change_ui` measures whether the visible colour changed immediately after clicking text/media.
- `role_changes` is the async save/CMD feedback path; it can arrive slightly later without affecting visible paint.

## R42BF DB correction

R42BE imported old pywebview JSONL rows using only `role`. Older rows used `new_role`, so many old events were wrongly interpreted as `UNKNOWN`. R42BF reads both shapes:

```text
native:    role
pywebview: new_role
```

R42BF also rebuilds the sidecar event tables from the JSONL in compact form each sync. This keeps the DB usable even if the old JSONL contains thousands of duplicate click events from earlier buggy runs. The JSONL audit file itself is not deleted.

## Not the speed fix

Database GUIs and storage engines do not make the live page load faster. Use them after the role-plan and history are stable. For speed, the relevant references are native WebView2 structure and debugging tools, not WARC/archive/extractor/database GUIs.

## Next architecture target

The clean final design is:

```text
Review DB builds role plan once
        ↓
small selected-source JSON payload
        ↓
warm native WebView2 document-start painter
        ↓
immediate visual role edits
        ↓
async JSONL + SQLite sidecar persistence
```

Only after that is stable should the broader database layer become the main source of source records, review history, queues, and search.
