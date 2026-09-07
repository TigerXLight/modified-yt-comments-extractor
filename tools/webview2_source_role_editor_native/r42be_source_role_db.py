#!/usr/bin/env python3
"""R42BE source-role plan SQLite sidecar.

This is intentionally outside the live WebView2 paint path.  The native editor
still reads the fast JSON payload, while this helper builds a persistent SQLite
view of the same role rows and JSONL click changes for later Review DB work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROLES = {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK", "LOCATOR"}


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def role(value: object) -> str:
    value = clean(value).upper()
    return value if value in ROLES else "UNKNOWN"


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
    import re
    return clean(re.sub(r"[^a-z0-9]+", " ", normalize(value))).lower()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA temp_store=MEMORY")
    return con


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
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
            PRIMARY KEY(session_id, mode, row_index, edit_key)
        );
        CREATE INDEX IF NOT EXISTS idx_role_plan_rows_key ON role_plan_rows(edit_key, mode);
        CREATE INDEX IF NOT EXISTS idx_role_plan_rows_text ON role_plan_rows(normalized_text);
        CREATE INDEX IF NOT EXISTS idx_role_plan_rows_role ON role_plan_rows(mode, role);
        CREATE TABLE IF NOT EXISTS role_change_events (
            event_hash TEXT PRIMARY KEY,
            imported_at TEXT NOT NULL,
            source_file TEXT NOT NULL,
            line_no INTEGER NOT NULL,
            selected_url TEXT NOT NULL,
            mode TEXT NOT NULL,
            edit_key TEXT NOT NULL,
            role TEXT NOT NULL,
            source TEXT NOT NULL,
            text TEXT NOT NULL,
            ui_duration_ms INTEGER,
            raw_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_role_change_events_key ON role_change_events(edit_key, mode);
        CREATE INDEX IF NOT EXISTS idx_role_change_events_url ON role_change_events(selected_url);
        CREATE TABLE IF NOT EXISTS role_latest (
            selected_url TEXT NOT NULL,
            mode TEXT NOT NULL,
            edit_key TEXT NOT NULL,
            role TEXT NOT NULL,
            source TEXT NOT NULL,
            text TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(selected_url, mode, edit_key)
        );
        """
    )


def iter_changes(path: Path) -> Iterable[tuple[int, dict[str, Any], str]]:
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
            if isinstance(data.get("changes"), list):
                for ch in data.get("changes") or []:
                    if isinstance(ch, Mapping):
                        yield line_no, dict(ch), raw
            elif isinstance(data.get("change"), Mapping):
                yield line_no, dict(data["change"]), raw
            else:
                # Older/simpler event shape.
                yield line_no, dict(data), raw


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
            inserted_rows = 0
            for mode, rows in rows_by_mode.items():
                mode = "media" if str(mode).lower() == "media" else "semantic"
                role_key = "media_source_role" if mode == "media" else "semantic_role"
                for fallback_index, row in enumerate(rows or [], start=1):
                    if not isinstance(row, Mapping):
                        continue
                    text = clean(row.get("text") or row.get("url") or row.get("media_url"))
                    edit_key = clean(row.get("edit_key") or f"{mode}_{fallback_index}")
                    r = role(row.get(role_key) or row.get("active_role"))
                    con.execute(
                        """INSERT OR REPLACE INTO role_plan_rows(session_id, mode, row_index, edit_key, kind, role, semantic_role, media_source_role, active_role,
                             text, normalized_text, loose_text, text_len, url, media_url, provenance_status, missing_provenance_reason)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (session_id, mode, int(row.get("index") or fallback_index), edit_key, clean(row.get("kind") or "text").lower() or "text",
                         r, role(row.get("semantic_role")), role(row.get("media_source_role")), role(row.get("active_role") or r),
                         text, normalize(text), loose_normalize(text), len(text), clean(row.get("url")), clean(row.get("media_url")),
                         clean(row.get("provenance_status")), clean(row.get("missing_provenance_reason"))),
                    )
                    inserted_rows += 1
            imported_changes = 0
            latest_updates = 0
            for line_no, change, raw in iter_changes(changes_path) or []:
                event_hash = hashlib.sha256((str(changes_path) + "\0" + str(line_no) + "\0" + raw).encode("utf-8", "replace")).hexdigest()
                edit_key = clean(change.get("edit_key") or change.get("key"))
                mode = "media" if clean(change.get("mode")).lower() == "media" else "semantic"
                new_role = role(change.get("role"))
                change_url = clean(change.get("selected_url") or selected_url)
                text = clean(change.get("text"))
                source = clean(change.get("source"))
                ui_ms = change.get("ui_duration_ms")
                try:
                    ui_ms = int(ui_ms) if ui_ms is not None else None
                except Exception:
                    ui_ms = None
                cur = con.execute(
                    """INSERT OR IGNORE INTO role_change_events(event_hash, imported_at, source_file, line_no, selected_url, mode, edit_key, role, source, text, ui_duration_ms, raw_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (event_hash, now, str(changes_path), line_no, change_url, mode, edit_key, new_role, source, text, ui_ms, raw),
                )
                if cur.rowcount:
                    imported_changes += 1
                if edit_key:
                    con.execute(
                        """INSERT INTO role_latest(selected_url, mode, edit_key, role, source, text, updated_at)
                           VALUES(?,?,?,?,?,?,?)
                           ON CONFLICT(selected_url, mode, edit_key) DO UPDATE SET role=excluded.role, source=excluded.source, text=excluded.text, updated_at=excluded.updated_at""",
                        (change_url, mode, edit_key, new_role, source, text, now),
                    )
                    latest_updates += 1
        summary = {
            "ok": True,
            "schema": "r42be_source_role_plan_v1",
            "db_path": str(db_path),
            "payload_path": str(payload_path),
            "changes_path": str(changes_path),
            "session_id": session_id,
            "selected_url": selected_url,
            "plan_rows": inserted_rows,
            "imported_changes_new": imported_changes,
            "latest_updates_seen": latest_updates,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000),
        }
        if summary_path:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return summary
    finally:
        con.close()


def inspect_db(db_path: Path) -> dict[str, Any]:
    con = sqlite3.connect(str(db_path))
    try:
        out: dict[str, Any] = {"db_path": str(db_path)}
        for table in ["role_source_sessions", "role_plan_rows", "role_change_events", "role_latest"]:
            try:
                out[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception as exc:
                out[table] = f"error: {exc}"
        try:
            out["latest_sessions"] = [dict(zip([c[0] for c in cur.description], row)) for cur in [con.execute("SELECT session_id, selected_url, semantic_rows, media_rows, updated_at FROM role_source_sessions ORDER BY updated_at DESC LIMIT 5")] for row in cur.fetchall()]
        except Exception:
            pass
        return out
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync/inspect the R42BE source-role SQLite sidecar DB")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sync = sub.add_parser("sync")
    sync.add_argument("--root", required=True)
    sync.add_argument("--payload", required=True)
    sync.add_argument("--changes", required=True)
    sync.add_argument("--db", required=True)
    sync.add_argument("--summary", default="")
    insp = sub.add_parser("inspect")
    insp.add_argument("--db", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "sync":
        summary = sync_db(Path(args.root), Path(args.payload), Path(args.changes), Path(args.db), Path(args.summary) if args.summary else None)
    else:
        summary = inspect_db(Path(args.db))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
