#!/usr/bin/env python3
"""R42BR source-role plan SQLite sidecar.

The live WebView2 editor still paints from the JSON payload.  SQLite remains a
sidecar for structure, durable review state, compacted change history, and
workflow inspection.  R42BR adds a current-plan table and token/schema-aware
change import so speed metrics are no longer blurred by old JSONL spam.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROLES = {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK", "LOCATOR"}
SCHEMA = "r42br_source_role_plan_v3"


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def role(value: object) -> str:
    value = clean(value).upper()
    return value if value in ROLES else "UNKNOWN"


def change_role(change: Mapping[str, Any]) -> str:
    return role(change.get("role") or change.get("new_role") or change.get("newRole"))


def normalize(value: object) -> str:
    text = clean(value)
    trans = str.maketrans({
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-",
        "\u00a0": " ",
    })
    return clean(text.translate(trans)).lower()


def loose_normalize(value: object) -> str:
    return clean(re.sub(r"[^a-z0-9]+", " ", normalize(value))).lower()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA temp_store=MEMORY")
    con.row_factory = sqlite3.Row
    return con


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT INTO schema_meta(key, value) VALUES('schema', 'r42br_source_role_plan_v3')
          ON CONFLICT(key) DO UPDATE SET value=excluded.value;

        CREATE TABLE IF NOT EXISTS role_source_sessions (
            session_id TEXT PRIMARY KEY,
            selected_url TEXT NOT NULL,
            title TEXT NOT NULL,
            payload_path TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            changes_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            semantic_rows INTEGER NOT NULL DEFAULT 0,
            media_rows INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS role_plan_rows (
            session_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            edit_key TEXT NOT NULL,
            kind TEXT NOT NULL,
            role TEXT NOT NULL,
            semantic_role TEXT NOT NULL,
            media_source_role TEXT NOT NULL,
            active_role TEXT NOT NULL,
            text TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            loose_text TEXT NOT NULL,
            text_len INTEGER NOT NULL,
            url TEXT NOT NULL,
            media_url TEXT NOT NULL,
            provenance_status TEXT NOT NULL,
            missing_provenance_reason TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(session_id, mode, row_index, edit_key)
        );
        CREATE INDEX IF NOT EXISTS idx_role_plan_rows_key ON role_plan_rows(edit_key, mode);
        CREATE INDEX IF NOT EXISTS idx_role_plan_rows_text ON role_plan_rows(normalized_text);
        CREATE INDEX IF NOT EXISTS idx_role_plan_rows_role ON role_plan_rows(mode, role);
        """
    )
    # Older R42BF DBs may already have role_plan_rows without these v3 columns.
    for ddl in [
        "ALTER TABLE role_plan_rows ADD COLUMN payload_sha256 TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE role_plan_rows ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
    ]:
        try:
            con.execute(ddl)
        except sqlite3.OperationalError:
            pass
    con.executescript(
        """
        DROP TABLE IF EXISTS role_plan_current;
        CREATE TABLE role_plan_current (
            selected_url TEXT NOT NULL,
            mode TEXT NOT NULL,
            edit_key TEXT NOT NULL,
            session_id TEXT NOT NULL,
            row_index INTEGER NOT NULL,
            kind TEXT NOT NULL,
            role TEXT NOT NULL,
            semantic_role TEXT NOT NULL,
            media_source_role TEXT NOT NULL,
            active_role TEXT NOT NULL,
            text TEXT NOT NULL,
            normalized_text TEXT NOT NULL,
            loose_text TEXT NOT NULL,
            text_len INTEGER NOT NULL,
            url TEXT NOT NULL,
            media_url TEXT NOT NULL,
            provenance_status TEXT NOT NULL,
            missing_provenance_reason TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(selected_url, mode, edit_key)
        );
        CREATE INDEX idx_role_plan_current_role ON role_plan_current(mode, role);
        CREATE INDEX idx_role_plan_current_text ON role_plan_current(normalized_text);

        DROP TABLE IF EXISTS role_change_events;
        DROP TABLE IF EXISTS role_latest;
        CREATE TABLE role_change_events (
            event_hash TEXT PRIMARY KEY,
            imported_at TEXT NOT NULL,
            source_file TEXT NOT NULL,
            line_no INTEGER NOT NULL,
            item_index INTEGER NOT NULL,
            selected_url TEXT NOT NULL,
            mode TEXT NOT NULL,
            edit_key TEXT NOT NULL,
            old_role TEXT NOT NULL,
            role TEXT NOT NULL,
            source TEXT NOT NULL,
            text TEXT NOT NULL,
            event_ts TEXT NOT NULL,
            page_at_ms INTEGER,
            ui_duration_ms INTEGER,
            app_marker TEXT NOT NULL DEFAULT '',
            native_schema TEXT NOT NULL DEFAULT '',
            command_token TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL
        );
        CREATE INDEX idx_role_change_events_key ON role_change_events(edit_key, mode);
        CREATE INDEX idx_role_change_events_url ON role_change_events(selected_url);
        CREATE INDEX idx_role_change_events_role ON role_change_events(mode, role);
        CREATE INDEX idx_role_change_events_token ON role_change_events(command_token);
        CREATE INDEX idx_role_change_events_marker ON role_change_events(app_marker, native_schema);

        CREATE TABLE role_latest (
            selected_url TEXT NOT NULL,
            mode TEXT NOT NULL,
            edit_key TEXT NOT NULL,
            role TEXT NOT NULL,
            source TEXT NOT NULL,
            text TEXT NOT NULL,
            app_marker TEXT NOT NULL DEFAULT '',
            native_schema TEXT NOT NULL DEFAULT '',
            command_token TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY(selected_url, mode, edit_key)
        );

        CREATE TABLE IF NOT EXISTS db_maintenance_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            keep_sessions_per_url INTEGER NOT NULL,
            keep_events INTEGER NOT NULL,
            vacuum_requested INTEGER NOT NULL,
            archived_sessions INTEGER NOT NULL,
            archived_plan_rows INTEGER NOT NULL,
            archived_change_events INTEGER NOT NULL,
            deleted_sessions INTEGER NOT NULL,
            deleted_plan_rows INTEGER NOT NULL,
            deleted_change_events INTEGER NOT NULL,
            db_size_before INTEGER NOT NULL,
            db_size_after INTEGER NOT NULL,
            elapsed_ms INTEGER NOT NULL,
            summary_json TEXT NOT NULL
        );
        """
    )
    _ensure_archive_tables(con)


def _extra_object(data: Mapping[str, Any]) -> Mapping[str, Any]:
    extra = data.get("extra")
    return extra if isinstance(extra, Mapping) else {}


def iter_changes(path: Path) -> Iterable[tuple[int, int, dict[str, Any], str, dict[str, Any]]]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line_no, line in enumerate(fh, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if not isinstance(data, Mapping):
                continue
            extra = _extra_object(data)
            parent = {
                "type": data.get("type"),
                "marker": data.get("marker"),
                "native_schema": data.get("native_schema"),
                "command_token": data.get("command_token") or extra.get("token"),
                "at_ms": data.get("at_ms"),
                "since_bootstrap_ms": data.get("since_bootstrap_ms"),
                "href": data.get("href"),
                "readyState": data.get("readyState"),
            }
            if isinstance(data.get("changes"), list):
                for item_index, ch in enumerate(data.get("changes") or []):
                    if isinstance(ch, Mapping):
                        yield line_no, item_index, dict(ch), raw, parent
            elif isinstance(data.get("change"), Mapping):
                yield line_no, 0, dict(data["change"]), raw, parent
            else:
                yield line_no, 0, dict(data), raw, parent




def _table_columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in con.execute(f"PRAGMA table_info({table})")]


def _ensure_archive_table(con: sqlite3.Connection, src_table: str, archive_table: str) -> None:
    con.execute(f"CREATE TABLE IF NOT EXISTS {archive_table} AS SELECT * FROM {src_table} WHERE 0")
    src_cols = _table_columns(con, src_table)
    arc_cols = _table_columns(con, archive_table)
    for col in src_cols:
        if col not in arc_cols:
            # Archive tables are internal/debug-only.  TEXT is safest for forward-compatible additions.
            con.execute(f"ALTER TABLE {archive_table} ADD COLUMN {col} TEXT")


def _ensure_archive_tables(con: sqlite3.Connection) -> None:
    # These archive tables keep old DB rows out of the hot/current tables without
    # deleting the raw JSONL audit trail.  They are not used by first paint.
    for src_table, archive_table in [
        ("role_source_sessions", "role_source_sessions_archive"),
        ("role_plan_rows", "role_plan_rows_archive"),
        ("role_change_events", "role_change_events_archive"),
    ]:
        try:
            _ensure_archive_table(con, src_table, archive_table)
        except Exception:
            # Schema creation should not break the editor-side sync path.
            pass


def _copy_rows_to_archive(con: sqlite3.Connection, src_table: str, archive_table: str, where_sql: str, params: tuple[Any, ...]) -> int:
    _ensure_archive_table(con, src_table, archive_table)
    cols = [c for c in _table_columns(con, src_table) if c in _table_columns(con, archive_table)]
    if not cols:
        return 0
    quoted = ", ".join(cols)
    before = con.execute(f"SELECT COUNT(*) FROM {archive_table}").fetchone()[0]
    con.execute(f"INSERT OR IGNORE INTO {archive_table} ({quoted}) SELECT {quoted} FROM {src_table} WHERE {where_sql}", params)
    after = con.execute(f"SELECT COUNT(*) FROM {archive_table}").fetchone()[0]
    return max(0, int(after or 0) - int(before or 0))


def _db_file_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except Exception:
        return 0


def maintain_db(db_path: Path, *, keep_sessions_per_url: int = 25, keep_events: int = 5000, vacuum: bool = False) -> dict[str, Any]:
    """Prune/compact the SQLite sidecar without touching the raw JSONL audit file.

    Current state is preserved in role_plan_current and role_latest.  Older
    historical DB rows are copied to *_archive tables before removal from the
    hot tables, then SQLite statistics/checkpoint work is run.  VACUUM is manual
    because it can be slower and may need an exclusive DB lock on Windows.
    """
    t0 = time.perf_counter()
    db_path = Path(db_path)
    before = _db_file_size(db_path)
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    keep_sessions_per_url = max(1, int(keep_sessions_per_url or 25))
    keep_events = max(0, int(keep_events or 0))
    con = open_db(db_path)
    try:
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.execute("INSERT INTO schema_meta(key, value) VALUES('schema', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (SCHEMA,))
        # Do not call ensure_schema() here: sync uses it to rebuild current/compact
        # tables from payload+JSONL, while maintenance must preserve the existing
        # current plan, latest roles, and compact events.  Only create archive/
        # maintenance tables if they are missing.
        _ensure_archive_tables(con)
        con.execute("""CREATE TABLE IF NOT EXISTS db_maintenance_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            keep_sessions_per_url INTEGER NOT NULL,
            keep_events INTEGER NOT NULL,
            vacuum_requested INTEGER NOT NULL,
            archived_sessions INTEGER NOT NULL,
            archived_plan_rows INTEGER NOT NULL,
            archived_change_events INTEGER NOT NULL,
            deleted_sessions INTEGER NOT NULL,
            deleted_plan_rows INTEGER NOT NULL,
            deleted_change_events INTEGER NOT NULL,
            db_size_before INTEGER NOT NULL,
            db_size_after INTEGER NOT NULL,
            elapsed_ms INTEGER NOT NULL,
            summary_json TEXT NOT NULL
        )""")
        archived_sessions = archived_plan_rows = archived_change_events = 0
        deleted_sessions = deleted_plan_rows = deleted_change_events = 0
        with con:
            _ensure_archive_tables(con)
            old_sessions = [row[0] for row in con.execute(
                """
                SELECT session_id FROM (
                  SELECT session_id, selected_url, updated_at,
                         ROW_NUMBER() OVER (PARTITION BY selected_url ORDER BY updated_at DESC, session_id DESC) AS rn
                  FROM role_source_sessions
                ) WHERE rn > ?
                """,
                (keep_sessions_per_url,),
            )]
            if old_sessions:
                placeholders = ",".join("?" for _ in old_sessions)
                archived_plan_rows = _copy_rows_to_archive(con, "role_plan_rows", "role_plan_rows_archive", f"session_id IN ({placeholders})", tuple(old_sessions))
                archived_sessions = _copy_rows_to_archive(con, "role_source_sessions", "role_source_sessions_archive", f"session_id IN ({placeholders})", tuple(old_sessions))
                cur = con.execute(f"DELETE FROM role_plan_rows WHERE session_id IN ({placeholders})", tuple(old_sessions))
                deleted_plan_rows = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0
                cur = con.execute(f"DELETE FROM role_source_sessions WHERE session_id IN ({placeholders})", tuple(old_sessions))
                deleted_sessions = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0

            if keep_events > 0:
                # Keep the newest compact DB events in the hot table.  Raw JSONL remains untouched.
                old_event_hashes = [row[0] for row in con.execute(
                    """
                    SELECT event_hash FROM role_change_events
                    ORDER BY line_no DESC, item_index DESC, event_hash DESC
                    LIMIT -1 OFFSET ?
                    """,
                    (keep_events,),
                )]
                if old_event_hashes:
                    placeholders = ",".join("?" for _ in old_event_hashes)
                    archived_change_events = _copy_rows_to_archive(con, "role_change_events", "role_change_events_archive", f"event_hash IN ({placeholders})", tuple(old_event_hashes))
                    cur = con.execute(f"DELETE FROM role_change_events WHERE event_hash IN ({placeholders})", tuple(old_event_hashes))
                    deleted_change_events = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else 0

        # Maintenance outside the transaction keeps lock windows small.
        try:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        try:
            con.execute("ANALYZE")
        except Exception:
            pass
        try:
            con.execute("PRAGMA optimize")
        except Exception:
            pass
        if vacuum:
            try:
                con.execute("VACUUM")
            except Exception as exc:
                vacuum_error = str(exc)
            else:
                vacuum_error = ""
        else:
            vacuum_error = "not_requested"
        # R42BR: on Windows the file-size shrink from VACUUM may not be visible
        # until the connection is fully closed.  Close/reopen before reporting
        # db_size_after so maintain output matches the next inspect command.
        try:
            con.commit()
        except Exception:
            pass
        try:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        try:
            con.close()
        except Exception:
            pass
        con = open_db(db_path)
        try:
            con.execute("PRAGMA busy_timeout=5000")
        except Exception:
            pass
        after = _db_file_size(db_path)
        summary = {
            "ok": True,
            "schema": SCHEMA,
            "db_path": str(db_path),
            "keep_sessions_per_url": keep_sessions_per_url,
            "keep_events": keep_events,
            "vacuum_requested": bool(vacuum),
            "vacuum_error": vacuum_error,
            "archived_sessions": archived_sessions,
            "archived_plan_rows": archived_plan_rows,
            "archived_change_events": archived_change_events,
            "deleted_sessions": deleted_sessions,
            "deleted_plan_rows": deleted_plan_rows,
            "deleted_change_events": deleted_change_events,
            "db_size_before": before,
            "db_size_after": after,
            "db_size_after_rechecked_after_reopen": True,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        }
        run_id = sha256_text(json.dumps(summary, sort_keys=True) + now)[:16]
        try:
            with con:
                con.execute(
                    """INSERT OR REPLACE INTO db_maintenance_runs(run_id, started_at, finished_at, keep_sessions_per_url, keep_events, vacuum_requested,
                         archived_sessions, archived_plan_rows, archived_change_events, deleted_sessions, deleted_plan_rows, deleted_change_events,
                         db_size_before, db_size_after, elapsed_ms, summary_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run_id, now, time.strftime("%Y-%m-%dT%H:%M:%S%z"), keep_sessions_per_url, keep_events, 1 if vacuum else 0,
                     archived_sessions, archived_plan_rows, archived_change_events, deleted_sessions, deleted_plan_rows, deleted_change_events,
                     before, after, summary["elapsed_ms"], json.dumps(summary, ensure_ascii=False, sort_keys=True)),
                )
        except Exception:
            pass
        return summary
    finally:
        con.close()

def sync_db(root: Path, payload_path: Path, changes_path: Path, db_path: Path, summary_path: Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    payload = json.loads(payload_path.read_text(encoding="utf-8", errors="replace"))
    selected_url = clean(payload.get("selected_url") or payload.get("title"))
    payload_hash = sha256_file(payload_path)
    session_id = payload_hash[:16]
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    rows_by_mode = payload.get("rows_by_mode") or {}
    title = clean(payload.get("title") or selected_url)

    con = open_db(db_path)
    try:
        ensure_schema(con)
        with con:
            con.execute(
                """INSERT INTO role_source_sessions(session_id, selected_url, title, payload_path, payload_sha256, changes_path, created_at, updated_at, semantic_rows, media_rows)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(session_id) DO UPDATE SET selected_url=excluded.selected_url, title=excluded.title,
                     payload_path=excluded.payload_path, payload_sha256=excluded.payload_sha256,
                     changes_path=excluded.changes_path, updated_at=excluded.updated_at,
                     semantic_rows=excluded.semantic_rows, media_rows=excluded.media_rows""",
                (session_id, selected_url, title, str(payload_path), payload_hash, str(changes_path), now, now,
                 len(rows_by_mode.get("semantic") or []), len(rows_by_mode.get("media") or [])),
            )
            con.execute("DELETE FROM role_plan_rows WHERE session_id=?", (session_id,))
            con.execute("DELETE FROM role_plan_current WHERE selected_url=?", (selected_url,))
            inserted_rows = 0
            current_rows = 0
            for mode_name, rows in rows_by_mode.items():
                mode = "media" if str(mode_name).lower() == "media" else "semantic"
                role_key = "media_source_role" if mode == "media" else "semantic_role"
                for fallback_index, row in enumerate(rows or [], start=1):
                    if not isinstance(row, Mapping):
                        continue
                    text = clean(row.get("text") or row.get("url") or row.get("media_url"))
                    edit_key = clean(row.get("edit_key") or f"{mode}_{fallback_index}")
                    r = role(row.get(role_key) or row.get("active_role"))
                    values = (
                        session_id, mode, int(row.get("index") or fallback_index), edit_key, clean(row.get("kind") or "text").lower() or "text",
                        r, role(row.get("semantic_role")), role(row.get("media_source_role")), role(row.get("active_role") or r),
                        text, normalize(text), loose_normalize(text), len(text), clean(row.get("url")), clean(row.get("media_url")),
                        clean(row.get("provenance_status")), clean(row.get("missing_provenance_reason")), payload_hash, now,
                    )
                    con.execute(
                        """INSERT OR REPLACE INTO role_plan_rows(session_id, mode, row_index, edit_key, kind, role, semantic_role, media_source_role, active_role,
                             text, normalized_text, loose_text, text_len, url, media_url, provenance_status, missing_provenance_reason, payload_sha256, updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        values,
                    )
                    con.execute(
                        """INSERT OR REPLACE INTO role_plan_current(selected_url, mode, edit_key, session_id, row_index, kind, role, semantic_role, media_source_role, active_role,
                             text, normalized_text, loose_text, text_len, url, media_url, provenance_status, missing_provenance_reason, payload_sha256, updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (selected_url, mode, edit_key, values[0], values[2]) + values[4:],
                    )
                    inserted_rows += 1
                    current_rows += 1

            raw_items_seen = 0
            imported_changes = 0
            compact_duplicates = 0
            latest_updates = 0
            seen_hashes: set[str] = set()
            current_marker_changes = 0
            for line_no, item_index, change, raw, parent in iter_changes(changes_path) or []:
                raw_items_seen += 1
                edit_key = clean(change.get("edit_key") or change.get("key"))
                mode = "media" if clean(change.get("mode")).lower() == "media" else "semantic"
                new_role = change_role(change)
                old_role = role(change.get("old_role") or change.get("oldRole"))
                change_url = clean(change.get("selected_url") or parent.get("href") or selected_url)
                text = clean(change.get("text"))
                source = clean(change.get("source"))
                event_ts = clean(change.get("ts") or change.get("timestamp") or parent.get("at_ms") or "")
                app_marker = clean(change.get("app_marker") or parent.get("marker"))
                native_schema = clean(change.get("native_schema") or parent.get("native_schema"))
                command_token = clean(change.get("command_token") or parent.get("command_token"))
                if native_schema == "r42br" or "R42BR" in app_marker:
                    current_marker_changes += 1
                page_at_ms = parent.get("at_ms")
                try:
                    page_at_ms = int(page_at_ms) if page_at_ms is not None else None
                except Exception:
                    page_at_ms = None
                ui_ms = change.get("ui_duration_ms")
                try:
                    ui_ms = int(ui_ms) if ui_ms is not None else None
                except Exception:
                    ui_ms = None
                identity = "\0".join([
                    change_url, mode, edit_key, old_role, new_role, source, text,
                    event_ts, str(page_at_ms if page_at_ms is not None else ""), str(item_index),
                    str(ui_ms if ui_ms is not None else ""), app_marker, native_schema, command_token,
                ])
                event_hash = sha256_text(identity)
                if event_hash in seen_hashes:
                    compact_duplicates += 1
                    continue
                seen_hashes.add(event_hash)
                cur = con.execute(
                    """INSERT OR IGNORE INTO role_change_events(event_hash, imported_at, source_file, line_no, item_index, selected_url, mode, edit_key, old_role, role, source, text, event_ts, page_at_ms, ui_duration_ms, app_marker, native_schema, command_token, raw_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (event_hash, now, str(changes_path), line_no, item_index, change_url, mode, edit_key, old_role, new_role, source, text, event_ts, page_at_ms, ui_ms, app_marker, native_schema, command_token, raw),
                )
                if cur.rowcount:
                    imported_changes += 1
                if edit_key:
                    con.execute(
                        """INSERT INTO role_latest(selected_url, mode, edit_key, role, source, text, app_marker, native_schema, command_token, updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(selected_url, mode, edit_key) DO UPDATE SET role=excluded.role, source=excluded.source, text=excluded.text,
                             app_marker=excluded.app_marker, native_schema=excluded.native_schema, command_token=excluded.command_token, updated_at=excluded.updated_at""",
                        (change_url, mode, edit_key, new_role, source, text, app_marker, native_schema, command_token, now),
                    )
                    latest_updates += 1
        summary = {
            "ok": True,
            "schema": SCHEMA,
            "db_path": str(db_path),
            "payload_path": str(payload_path),
            "changes_path": str(changes_path),
            "session_id": session_id,
            "selected_url": selected_url,
            "plan_rows": inserted_rows,
            "current_plan_rows": current_rows,
            "raw_change_items_seen": raw_items_seen,
            "imported_compact_changes": imported_changes,
            "compact_duplicates_skipped": compact_duplicates,
            "latest_updates_seen": latest_updates,
            "current_marker_changes_seen": current_marker_changes,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        }
        if summary_path:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return summary
    finally:
        con.close()


def _one(con: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = con.execute(sql, params).fetchone()
    return row[0] if row else None


def _duration_summary(con: sqlite3.Connection, where: str = "", params: tuple[Any, ...] = ()) -> dict[str, Any]:
    sql = "SELECT COUNT(*) AS count, MIN(ui_duration_ms) AS min, MAX(ui_duration_ms) AS max, ROUND(AVG(ui_duration_ms),1) AS avg FROM role_change_events WHERE ui_duration_ms IS NOT NULL"
    if where:
        sql += " AND " + where
    row = con.execute(sql, params).fetchone()
    return dict(row) if row else {}


def _duration_latest(con: sqlite3.Connection, limit: int = 50, where: str = "", params: tuple[Any, ...] = ()) -> dict[str, Any]:
    sql = """SELECT COUNT(*) AS count, MIN(ui_duration_ms) AS min, MAX(ui_duration_ms) AS max, ROUND(AVG(ui_duration_ms),1) AS avg
             FROM (SELECT ui_duration_ms FROM role_change_events WHERE ui_duration_ms IS NOT NULL {where_clause}
                   ORDER BY line_no DESC, item_index DESC LIMIT ?)"""
    where_clause = (" AND " + where) if where else ""
    row = con.execute(sql.format(where_clause=where_clause), params + (limit,)).fetchone()
    return dict(row) if row else {}


def inspect_db(db_path: Path) -> dict[str, Any]:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        out: dict[str, Any] = {"db_path": str(db_path)}
        out["db_size_bytes"] = _db_file_size(db_path)
        for table in ["role_source_sessions", "role_plan_rows", "role_plan_current", "role_change_events", "role_latest", "role_source_sessions_archive", "role_plan_rows_archive", "role_change_events_archive", "db_maintenance_runs"]:
            try:
                out[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception as exc:
                out[table] = {"error": str(exc)}
        try:
            out["schema"] = con.execute("SELECT value FROM schema_meta WHERE key='schema'").fetchone()[0]
        except Exception:
            out["schema"] = "unknown"
        try:
            out["latest_sessions"] = [dict(row) for row in con.execute(
                """SELECT session_id, selected_url, semantic_rows, media_rows, updated_at
                   FROM role_source_sessions ORDER BY updated_at DESC LIMIT 5"""
            )]
        except Exception:
            out["latest_sessions"] = []
        try:
            out["current_plan_role_counts"] = [dict(row) for row in con.execute(
                "SELECT mode, role, COUNT(*) AS count FROM role_plan_current GROUP BY mode, role ORDER BY mode, role"
            )]
        except Exception:
            out["current_plan_role_counts"] = []
        try:
            out["latest_roles"] = [dict(row) for row in con.execute(
                """SELECT mode, role, source, native_schema, substr(command_token,1,40) AS command_token, edit_key, substr(text,1,90) AS text
                   FROM role_latest ORDER BY mode, edit_key LIMIT 20"""
            )]
        except Exception:
            out["latest_roles"] = []
        try:
            out["change_role_counts"] = [dict(row) for row in con.execute(
                "SELECT mode, role, COUNT(*) AS count FROM role_change_events GROUP BY mode, role ORDER BY mode, role"
            )]
        except Exception:
            out["change_role_counts"] = []
        try:
            out["change_schema_counts"] = [dict(row) for row in con.execute(
                "SELECT COALESCE(NULLIF(native_schema,''),'legacy') AS native_schema, COUNT(*) AS count FROM role_change_events GROUP BY COALESCE(NULLIF(native_schema,''),'legacy') ORDER BY native_schema"
            )]
        except Exception:
            out["change_schema_counts"] = []
        try:
            out["ui_duration_ms_all"] = _duration_summary(con)
            out["ui_duration_ms_latest_50"] = _duration_latest(con, 50)
            out["ui_duration_ms_r42br"] = _duration_summary(con, "native_schema='r42br' OR app_marker LIKE '%R42BR%'")
            out["ui_duration_ms_latest_50_r42br"] = _duration_latest(con, 50, "native_schema='r42br' OR app_marker LIKE '%R42BR%'")
        except Exception as exc:
            out["ui_duration_ms_error"] = str(exc)
        try:
            out["latest_change_events"] = [dict(row) for row in con.execute(
                """SELECT line_no, item_index, mode, role, source, ui_duration_ms, native_schema, substr(command_token,1,48) AS command_token, substr(text,1,90) AS text
                   FROM role_change_events ORDER BY line_no DESC, item_index DESC LIMIT 12"""
            )]
        except Exception:
            out["latest_change_events"] = []
        try:
            out["latest_maintenance_runs"] = [dict(row) for row in con.execute(
                """SELECT run_id, finished_at, keep_sessions_per_url, keep_events, vacuum_requested, archived_sessions, archived_plan_rows, archived_change_events, deleted_sessions, deleted_plan_rows, deleted_change_events, db_size_before, db_size_after, elapsed_ms
                   FROM db_maintenance_runs ORDER BY finished_at DESC LIMIT 5"""
            )]
        except Exception:
            out["latest_maintenance_runs"] = []
        return out
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R42BR source-role SQLite sidecar")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_sync = sub.add_parser("sync")
    p_sync.add_argument("--root", required=True)
    p_sync.add_argument("--payload", required=True)
    p_sync.add_argument("--changes", required=True)
    p_sync.add_argument("--db", required=True)
    p_sync.add_argument("--summary", default="")
    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("--db", required=True)
    p_maintain = sub.add_parser("maintain")
    p_maintain.add_argument("--db", required=True)
    p_maintain.add_argument("--keep-sessions-per-url", type=int, default=25)
    p_maintain.add_argument("--keep-events", type=int, default=5000)
    p_maintain.add_argument("--vacuum", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "sync":
        summary = sync_db(Path(args.root), Path(args.payload), Path(args.changes), Path(args.db), Path(args.summary) if args.summary else None)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "inspect":
        print(json.dumps(inspect_db(Path(args.db)), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "maintain":
        print(json.dumps(maintain_db(Path(args.db), keep_sessions_per_url=args.keep_sessions_per_url, keep_events=args.keep_events, vacuum=args.vacuum), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
