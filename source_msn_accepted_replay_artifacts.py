from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import shutil
import time
import webbrowser
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


CASE_ID = "msn_york_mosque_20260812"
SCHEMA_VERSION = "msn_background_accepted_replay_references_v1"
REFERENCE_ROOT_NAME = "accepted_msn_replay_artifacts"
BUNDLE_BASENAME = "YTCE_NEXT_SESSION_UPLOAD_BUNDLE_20260812_MSN_CLOSEOUT"


@dataclass(frozen=True)
class ReferenceSpec:
    label: str
    role: str
    source_path: str
    bundle_path: str
    expected_sha256: str = ""
    required: bool = False


@dataclass(frozen=True)
class ReferenceCheck:
    label: str
    role: str
    source_path: str
    bundle_path: str
    exists: bool
    kind: str
    size_bytes: int | None
    sha256: str
    expected_sha256: str
    required: bool


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parent


def artifact_root(repo_root: str | Path | None = None) -> Path:
    root = Path(repo_root) if repo_root is not None else repo_root_from_here()
    return root / REFERENCE_ROOT_NAME / CASE_ID


def default_reference_specs() -> list[ReferenceSpec]:
    user = Path(os.environ.get("USERPROFILE", r"C:\Users\fahad"))
    local = Path(os.environ.get("LOCALAPPDATA", str(user / "AppData" / "Local")))
    return [
        ReferenceSpec(
            label="Comments V15 stitch output folder",
            role="Folder containing accepted total comments stitched screenshot reference.",
            source_path=str(user / "Downloads" / "MSN_YORK_ANDROID_COMMENTS_V15_COOKIE_STRIPPED_STITCH_20260811_045759"),
            bundle_path="01_comments_v15_stitch_output_folder",
        ),
        ReferenceSpec(
            label="Accepted total comments stitched screenshot",
            role="Accepted total comments screenshot reference.",
            source_path=str(user / "Downloads" / "MSN_YORK_ANDROID_COMMENTS_V15_COOKIE_STRIPPED_STITCH_20260811_045759" / "screenshots" / "android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png"),
            bundle_path="02_accepted_reference_screenshots/android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png",
            required=True,
        ),
        ReferenceSpec(
            label="Comments V15 instruction ZIP",
            role="Original instruction ZIP for comments stitch capture.",
            source_path=str(user / "Downloads" / "MSN_YORK_ANDROID_COMMENTS_V15_COOKIE_STRIPPED_STITCH_20260811.zip"),
            bundle_path="03_instruction_zips/MSN_YORK_ANDROID_COMMENTS_V15_COOKIE_STRIPPED_STITCH_20260811.zip",
        ),
        ReferenceSpec(
            label="Article V6 print-layout output folder",
            role="Folder containing accepted article screenshot reference.",
            source_path=str(user / "Downloads" / "MSN_YORK_ANDROID_COMMENTS_PRINT_LAYOUT_GATE_V6_20260811_032334"),
            bundle_path="04_article_v6_print_layout_output_folder",
        ),
        ReferenceSpec(
            label="Accepted article screenshot reference",
            role="Accepted article screenshot reference from print-layout gate.",
            source_path=str(user / "Downloads" / "MSN_YORK_ANDROID_COMMENTS_PRINT_LAYOUT_GATE_V6_20260811_032334" / "screenshots" / "android_article_MAIN_SINGLE_reference_style.png"),
            bundle_path="02_accepted_reference_screenshots/android_article_MAIN_SINGLE_reference_style_from_v6.png",
            required=True,
        ),
        ReferenceSpec(
            label="Article V6 strict internal scroll instruction ZIP",
            role="Original instruction ZIP for accepted article screenshot capture.",
            source_path=str(user / "Downloads" / "MSN_YORK_ANDROID_COMMENTS_PRINT_LAYOUT_GATE_V6_STRICT_INTERNAL_SCROLL_20260811.zip"),
            bundle_path="03_instruction_zips/MSN_YORK_ANDROID_COMMENTS_PRINT_LAYOUT_GATE_V6_STRICT_INTERNAL_SCROLL_20260811.zip",
        ),
        ReferenceSpec(
            label="Closeout accepted article screenshot",
            role="Accepted article screenshot from hardened closeout output.",
            source_path=str(local / "Temp" / "msn_york_adapter_closeout_replay_hardened_12902" / "screenshots" / "android_article_MAIN_SINGLE_reference_style.png"),
            bundle_path="02_accepted_reference_screenshots/android_article_MAIN_SINGLE_reference_style_from_closeout.png",
            required=True,
        ),
        ReferenceSpec(
            label="Closeout accepted comments screenshot",
            role="Accepted comments screenshot from hardened closeout output.",
            source_path=str(local / "Temp" / "msn_york_adapter_closeout_replay_hardened_12902" / "screenshots" / "android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png"),
            bundle_path="02_accepted_reference_screenshots/android_comments_all_expanded_SINGLE_INTERNAL_STITCH_from_closeout.png",
            required=True,
        ),
        ReferenceSpec(
            label="V34 filter snapshot HTML",
            role="V34 filter reference HTML.",
            source_path=str(local / "Temp" / "ytce_msn_manual_comments_modal_20260809_next" / "single_field_search_v34" / "msn-comments-v34-snapshot-accumulator-20260810031146.html"),
            bundle_path="05_v34_filter_reference/msn-comments-v34-snapshot-accumulator-20260810031146.html",
            required=True,
        ),
        ReferenceSpec(
            label="V34 snapshot accumulator instruction ZIP",
            role="Instruction ZIP for V34 snapshot accumulator.",
            source_path=str(user / "Downloads" / "MSN_COMMENTS_V34_SNAPSHOT_ACCUMULATOR_TEST_KIT_20260810.zip"),
            bundle_path="03_instruction_zips/MSN_COMMENTS_V34_SNAPSHOT_ACCUMULATOR_TEST_KIT_20260810.zip",
        ),
        ReferenceSpec(
            label="V34 pre-rebuilder output ZIP",
            role="Original V34 pre-rebuilder output reference ZIP.",
            source_path=str(user / "Downloads" / "V34 pre-rebuilder output.zip"),
            bundle_path="05_v34_filter_reference/V34 pre-rebuilder output.zip",
        ),
        ReferenceSpec(
            label="V35 profile stats HTML",
            role="V35 profile reference HTML.",
            source_path=str(local / "Temp" / "ytce_msn_manual_comments_modal_20260809_next" / "single_field_search_v35" / "msn-comments-v35-profile-stats-20260810032024.html"),
            bundle_path="06_v35_profile_reference/msn-comments-v35-profile-stats-20260810032024.html",
            required=True,
        ),
        ReferenceSpec(
            label="V35 profile stats rebuilder instruction ZIP",
            role="Instruction ZIP for V35 profile stats rebuilder.",
            source_path=str(user / "Downloads" / "MSN_COMMENTS_V35_PROFILE_STATS_REBUILDER_20260810.zip"),
            bundle_path="03_instruction_zips/MSN_COMMENTS_V35_PROFILE_STATS_REBUILDER_20260810.zip",
        ),
        ReferenceSpec(
            label="V35 accepted output reference ZIP",
            role="Accepted final V35 output reference ZIP.",
            source_path=str(user / "Downloads" / "Accepted final V35 outputreference.zip"),
            bundle_path="06_v35_profile_reference/Accepted final V35 outputreference.zip",
        ),
        ReferenceSpec(
            label="MSN York production ready closeout ZIP",
            role="Production-ready closeout archive after d098c64.",
            source_path=str(user / "Downloads" / "MSN_YORK_PRODUCTION_READY_CLOSEOUT_AFTER_D098C64_20260811_071407.zip"),
            bundle_path="07_production_ready_closeout/MSN_YORK_PRODUCTION_READY_CLOSEOUT_AFTER_D098C64_20260811_071407.zip",
            expected_sha256="D5BD9DDC4472D0DE5A91EE7D0B146E65DBB8B988811518F0A2D81E66593F81D7",
        ),
        ReferenceSpec(
            label="MSN production closeout source folder",
            role="Source folder archived by the production-ready closeout ZIP.",
            source_path=str(local / "Temp" / "msn_york_adapter_closeout_after_d098c64_20260811_071407"),
            bundle_path="07_production_ready_closeout/source_folder_msn_york_adapter_closeout_after_d098c64_20260811_071407",
        ),
        ReferenceSpec(
            label="Static/offline viewer closeout ZIP",
            role="Accepted static/offline viewer and static visual replay closeout ZIP.",
            source_path=str(user / "Downloads" / "MSN_OFFLINE_VIEWER_STATIC_REPLAY_CLOSEOUT_20260812_021527.zip"),
            bundle_path="08_static_offline_visual_closeout/MSN_OFFLINE_VIEWER_STATIC_REPLAY_CLOSEOUT_20260812_021527.zip",
            expected_sha256="531091DCB117688E83F1F32CCF956F94698F1CCA98510349500AF206EC6EB416",
            required=True,
        ),
        ReferenceSpec(
            label="Primary dynamic original-looking live_capture folder",
            role="Canonical dynamic/original-shell MSN ReplayWeb article candidate source folder.",
            source_path=str(local / "Temp" / "msn_york_adapter_closeout_replay_hardened_12902" / "live_capture"),
            bundle_path="09_primary_dynamic_original_shell_live_capture",
            required=True,
        ),
        ReferenceSpec(
            label="Primary dynamic original-looking WARC",
            role="Canonical dynamic/original-shell WARC: live_capture/browser_capture/local_web_archive/archive/data.warc.",
            source_path=str(local / "Temp" / "msn_york_adapter_closeout_replay_hardened_12902" / "live_capture" / "browser_capture" / "local_web_archive" / "archive" / "data.warc"),
            bundle_path="09_primary_dynamic_original_shell_live_capture/browser_capture/local_web_archive/archive/data.warc",
            required=True,
        ),
        ReferenceSpec(
            label="Desktop JSON-first fallback output folder",
            role="Fallback dynamic evidence route, not canonical original-shell view.",
            source_path=str(local / "Temp" / "msn_desktop_json_first_dynamic_recapture_v5"),
            bundle_path="10_fallback_desktop_json_first_dynamic_recapture_v5",
        ),
    ]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def directory_size(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def check_references(specs: Sequence[ReferenceSpec] | None = None) -> list[ReferenceCheck]:
    checks: list[ReferenceCheck] = []
    for spec in specs or default_reference_specs():
        path = Path(spec.source_path)
        exists = path.exists()
        kind = "missing"
        size: int | None = None
        digest = ""
        if exists and path.is_file():
            kind = "file"
            try:
                size = path.stat().st_size
                digest = sha256_file(path)
            except OSError:
                kind = "unreadable_file"
        elif exists and path.is_dir():
            kind = "directory"
            size = directory_size(path)
        checks.append(
            ReferenceCheck(
                label=spec.label,
                role=spec.role,
                source_path=str(path),
                bundle_path=spec.bundle_path,
                exists=exists,
                kind=kind,
                size_bytes=size,
                sha256=digest,
                expected_sha256=spec.expected_sha256,
                required=spec.required,
            )
        )
    return checks


def status_from_checks(checks: Sequence[ReferenceCheck]) -> str:
    required_missing = [c for c in checks if c.required and not c.exists]
    hash_mismatch = [c for c in checks if c.expected_sha256 and c.sha256 and c.sha256.upper() != c.expected_sha256.upper()]
    if required_missing:
        return "ACCEPTED_MSN_REPLAY_REFERENCES_REQUIRED_FILES_MISSING"
    if hash_mismatch:
        return "ACCEPTED_MSN_REPLAY_REFERENCES_HASH_MISMATCH"
    return "ACCEPTED_MSN_REPLAY_REFERENCES_READY"


def accepted_routes_summary() -> list[str]:
    return [
        "Primary dynamic/original-looking route: msn_york_adapter_closeout_replay_hardened_12902/live_capture, especially browser_capture/local_web_archive/archive/data.warc.",
        "Static/100% visual route: MSN_OFFLINE_VIEWER_STATIC_REPLAY_CLOSEOUT_20260812_021527.zip.",
        "Fallback dynamic evidence route: desktop JSON-first V5 output folder.",
        "Rejected/non-canonical routes: Android-only dynamic attempts, ArchiveWeb.page app/extension, manual-assisted V6, WACZ-only attempts.",
    ]


def limitations_summary() -> list[str]:
    return [
        "Dynamic/original-shell data.warc is the best original-looking ReplayWeb article candidate, not a complete infinite MSN feed replay.",
        "Static visual route is the 100% reliable visual preservation route.",
        "Desktop JSON-first replay is fallback evidence, not the canonical original-shell view.",
        "WACZ ReplayWeb success is not claimed.",
        "Actual comment text is preserved in JSON/text/static viewer outputs, but not as a fully dynamic MSN comment replay.",
        "Full infinite MSN feed replay is not required.",
    ]


def write_reference_index(repo_root: str | Path | None = None) -> Path:
    root = artifact_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    checks = check_references()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "case_id": CASE_ID,
        "status": status_from_checks(checks),
        "generated_at_unix": int(time.time()),
        "accepted_commit_notes": {
            "d098c64": "Fix MSN production closeout evidence gates",
            "78efdec": "Refine MSN dynamic recapture as desktop JSON-first article replay",
            "accepted_dynamic_route": "live_capture/browser_capture/local_web_archive/archive/data.warc",
            "accepted_static_route": "MSN_OFFLINE_VIEWER_STATIC_REPLAY_CLOSEOUT_20260812_021527.zip",
        },
        "accepted_routes": accepted_routes_summary(),
        "limitations": limitations_summary(),
        "references": [asdict(c) for c in checks],
    }
    path = root / "accepted-msn-replay-reference-index.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_reference_dashboard(path)
    return path


def write_reference_dashboard(index_path: str | Path) -> Path:
    index_path = Path(index_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    root = index_path.parent
    rows = []
    for ref in payload["references"]:
        status = "READY" if ref["exists"] else ("MISSING REQUIRED" if ref["required"] else "MISSING")
        sha = html.escape(ref["sha256"] or "")
        expected = html.escape(ref["expected_sha256"] or "")
        if expected and sha and sha.upper() != expected.upper():
            status = "HASH MISMATCH"
        rows.append(
            "<tr>"
            f"<td>{html.escape(ref['label'])}</td>"
            f"<td>{html.escape(status)}</td>"
            f"<td>{html.escape(ref['kind'])}</td>"
            f"<td>{html.escape(str(ref['size_bytes'] or ''))}</td>"
            f"<td><code>{sha}</code></td>"
            f"<td><code>{expected}</code></td>"
            f"<td>{html.escape(ref['role'])}</td>"
            f"<td><code>{html.escape(ref['source_path'])}</code></td>"
            f"<td><code>{html.escape(ref['bundle_path'])}</code></td>"
            "</tr>"
        )
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MSN accepted replay reference index</title>
<style>
body {{ margin: 18px; background:#111827; color:#e5e7eb; font-family: Arial, sans-serif; }}
h1,h2 {{ color:#f9fafb; }}
.panel {{ border:1px solid #374151; background:#1f2937; border-radius:8px; padding:12px; margin:12px 0; }}
.status {{ border-color:#2563eb; }}
.warn {{ border-color:#f59e0b; background:#3b2506; }}
table {{ border-collapse: collapse; width:100%; font-size:12px; }}
th,td {{ border:1px solid #374151; padding:6px; vertical-align:top; }}
th {{ background:#243244; }}
code {{ color:#93c5fd; word-break:break-all; }}
li {{ margin: 4px 0; }}
</style>
</head>
<body>
<h1>MSN accepted replay reference index</h1>
<div class="panel status">
<strong>Status:</strong> {html.escape(payload['status'])}<br>
<strong>Case:</strong> {html.escape(payload['case_id'])}<br>
<strong>Index:</strong> <code>{html.escape(str(index_path))}</code>
</div>
<div class="panel">
<h2>Accepted routes</h2>
<ul>{''.join('<li>'+html.escape(x)+'</li>' for x in payload['accepted_routes'])}</ul>
</div>
<div class="panel warn">
<h2>Limitations / closeout wording</h2>
<ul>{''.join('<li>'+html.escape(x)+'</li>' for x in payload['limitations'])}</ul>
</div>
<div class="panel">
<h2>Reference checks</h2>
<table>
<tr><th>Label</th><th>Status</th><th>Kind</th><th>Size</th><th>SHA-256</th><th>Expected SHA-256</th><th>Role</th><th>Source path</th><th>Bundle path</th></tr>
{''.join(rows)}
</table>
</div>
</body>
</html>
"""
    dashboard = root / "accepted-msn-replay-reference-dashboard.html"
    dashboard.write_text(body, encoding="utf-8")
    return dashboard


def _zip_file(z: zipfile.ZipFile, src: Path, arcname: str, missing: list[str]) -> None:
    if not src.exists():
        missing.append(str(src))
        return
    if src.is_file():
        z.write(src, arcname)
    elif src.is_dir():
        for item in sorted(src.rglob("*")):
            if item.is_file():
                rel = item.relative_to(src).as_posix()
                z.write(item, f"{arcname.rstrip('/')}/{rel}")


def make_next_session_upload_bundle(
    *,
    repo_root: str | Path | None = None,
    output_dir: str | Path | None = None,
    specs: Sequence[ReferenceSpec] | None = None,
) -> Path:
    specs = list(specs or default_reference_specs())
    output_dir = Path(output_dir) if output_dir is not None else Path(os.environ.get("USERPROFILE", ".")) / "Downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bundle_path = output_dir / f"{BUNDLE_BASENAME}_{stamp}.zip"

    index_path = write_reference_index(repo_root)
    checks = check_references(specs)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "case_id": CASE_ID,
        "created_at_unix": int(time.time()),
        "bundle_name": bundle_path.name,
        "status": status_from_checks(checks),
        "accepted_routes": accepted_routes_summary(),
        "limitations": limitations_summary(),
        "references": [asdict(c) for c in checks],
    }

    missing: list[str] = []
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as z:
        z.writestr("README_MSN_ACCEPTED_REPLAY_REFERENCES.md", render_bundle_readme(manifest))
        z.writestr("manifest/msn_accepted_replay_reference_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        z.write(index_path, "manifest/accepted-msn-replay-reference-index.json")
        dashboard = index_path.parent / "accepted-msn-replay-reference-dashboard.html"
        if dashboard.exists():
            z.write(dashboard, "manifest/accepted-msn-replay-reference-dashboard.html")
        for spec in specs:
            _zip_file(z, Path(spec.source_path), spec.bundle_path, missing)
        if missing:
            z.writestr("manifest/MISSING_REFERENCE_PATHS.txt", "\n".join(missing) + "\n")

    sha = sha256_file(bundle_path)
    sha_path = bundle_path.with_suffix(bundle_path.suffix + ".sha256.txt")
    sha_path.write_text(f"{sha}  {bundle_path.name}\n", encoding="utf-8")
    return bundle_path


def render_bundle_readme(manifest: Mapping[str, object]) -> str:
    routes = "\n".join(f"- {x}" for x in manifest.get("accepted_routes", []))
    limitations = "\n".join(f"- {x}" for x in manifest.get("limitations", []))
    return f"""# MSN accepted replay references bundle

Case: `{CASE_ID}`

This bundle is intended as the next-session upload/reference bundle for the MSN York mosque evidence workflow.

## Accepted routes

{routes}

## Limitations

{limitations}

## Important commits

- `d098c647b361b489a27456a4c3f965f71afb6a38` — Fix MSN production closeout evidence gates.
- `78efdec` — Refine MSN dynamic recapture as desktop JSON-first article replay.

## How to use

Upload this ZIP in the next session so the accepted screenshots, V34/V35 references, production closeout archive, static closeout archive, and primary dynamic live_capture folder are available together.
"""


def status_lines(repo_root: str | Path | None = None) -> list[str]:
    index = write_reference_index(repo_root)
    payload = json.loads(index.read_text(encoding="utf-8"))
    lines = [
        f"MSN_ACCEPTED_REPLAY_REFERENCE_STATUS={payload['status']}",
        f"MSN_ACCEPTED_REPLAY_REFERENCE_INDEX={index}",
        f"MSN_ACCEPTED_REPLAY_REFERENCE_DASHBOARD={index.parent / 'accepted-msn-replay-reference-dashboard.html'}",
        "",
        "Accepted routes:",
    ]
    lines.extend("- " + x for x in payload["accepted_routes"])
    lines.append("")
    lines.append("Limitations:")
    lines.extend("- " + x for x in payload["limitations"])
    lines.append("")
    lines.append("Reference checks:")
    for ref in payload["references"]:
        status = "READY" if ref["exists"] else ("MISSING REQUIRED" if ref["required"] else "MISSING")
        if ref["expected_sha256"] and ref["sha256"] and ref["expected_sha256"].upper() != ref["sha256"].upper():
            status = "HASH MISMATCH"
        lines.append(f"- {ref['label']}: {status} :: {ref['source_path']}")
    return lines


def open_dashboard(repo_root: str | Path | None = None) -> Path:
    index = write_reference_index(repo_root)
    dashboard = index.parent / "accepted-msn-replay-reference-dashboard.html"
    webbrowser.open(dashboard.as_uri())
    return dashboard


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--write-index", action="store_true")
    parser.add_argument("--open-dashboard", action="store_true")
    parser.add_argument("--make-upload-bundle", action="store_true")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo = args.repo_root or None
    if args.make_upload_bundle:
        bundle = make_next_session_upload_bundle(repo_root=repo, output_dir=args.output_dir or None)
        payload = {
            "bundle": str(bundle),
            "bundle_sha256": sha256_file(bundle),
            "sha256_file": str(bundle.with_suffix(bundle.suffix + ".sha256.txt")),
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("YTCE_NEXT_SESSION_UPLOAD_BUNDLE=" + payload["bundle"])
            print("YTCE_NEXT_SESSION_UPLOAD_BUNDLE_SHA256=" + payload["bundle_sha256"])
            print("YTCE_NEXT_SESSION_UPLOAD_BUNDLE_SHA256_FILE=" + payload["sha256_file"])
        return 0

    if args.open_dashboard:
        dashboard = open_dashboard(repo)
        print("MSN_ACCEPTED_REPLAY_REFERENCE_DASHBOARD_OPENED=" + str(dashboard))
        return 0

    if args.write_index or True:
        lines = status_lines(repo)
        if args.json:
            index = write_reference_index(repo)
            print(index.read_text(encoding="utf-8"))
        else:
            print("\n".join(lines))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
