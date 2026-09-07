#!/usr/bin/env python3
"""R42BG source-role plan SQLite sidecar.

The live WebView2 editor still paints from the JSON payload.  SQLite remains a
sidecar for structure, durable review state, compacted change history, and
workflow inspection.  R42BG adds a current-plan table and token/schema-aware
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
SCHEMA = "r42bg_source_role_plan_v3"


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
        INSERT INTO schema_meta(key, value) VALUES('schema', 'r42bg_source_role_plan_v3')
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
        """
    )


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
                if native_schema == "r42bg" or "R42BG" in app_marker:
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
        for table in ["role_source_sessions", "role_plan_rows", "role_plan_current", "role_change_events", "role_latest"]:
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
            out["ui_duration_ms_r42bg"] = _duration_summary(con, "native_schema='r42bg' OR app_marker LIKE '%R42BG%'")
            out["ui_duration_ms_latest_50_r42bg"] = _duration_latest(con, 50, "native_schema='r42bg' OR app_marker LIKE '%R42BG%'")
        except Exception as exc:
            out["ui_duration_ms_error"] = str(exc)
        try:
            out["latest_change_events"] = [dict(row) for row in con.execute(
                """SELECT line_no, item_index, mode, role, source, ui_duration_ms, native_schema, substr(command_token,1,48) AS command_token, substr(text,1,90) AS text
                   FROM role_change_events ORDER BY line_no DESC, item_index DESC LIMIT 12"""
            )]
        except Exception:
            out["latest_change_events"] = []
        return out
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R42BG source-role SQLite sidecar")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_sync = sub.add_parser("sync")
    p_sync.add_argument("--root", required=True)
    p_sync.add_argument("--payload", required=True)
    p_sync.add_argument("--changes", required=True)
    p_sync.add_argument("--db", required=True)
    p_sync.add_argument("--summary", default="")
    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("--db", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "sync":
        summary = sync_db(Path(args.root), Path(args.payload), Path(args.changes), Path(args.db), Path(args.summary) if args.summary else None)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "inspect":
        print(json.dumps(inspect_db(Path(args.db)), ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
