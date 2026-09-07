from __future__ import annotations
import datetime
import os
from pathlib import Path
import shutil
import zipfile

PROJECT_FILES = [
    'main.py',
    'source_adapters.py',
    'source_resource_state.py',
    'profile_media_archive_source_role_surface_r42ds.py',
    'profile_media_archive_source_role_surface_r42ds_test.py',
    'profile_media_normal_access_feature_receipts_r42dr.py',
    'profile_media_normal_access_provider_layer_r42dq.py',
    'profile_media_universal_worker_source_router_r42do.py',
    'profile_media_account_channel_worker_adapter_r42dp.py',
    'profile_media_normal_access_layer_r42dn.py',
    'profile_media_access_escalation_policy_r42dm.py',
    'profile_media_universal_source_link_adapter_r42dk.py',
    'profile_media_universal_source_link_adapter_r42dl.py',
    'profile_media_archive_material_chain_r42ct.py',
    'profile_media_link_source_details_role_matrix_v83d.py',
    'profile_media_link_source_webpage_role_view_v83d.py',
    'profile_media_link_source_real_webview_overlay_v83d.py',
    'R42DS_ARCHIVE_SOURCE_ROLES_WEBVIEW2_NOTES_20260907.md',
    'tools/webview2_source_role_editor_native/_r42ds_python.cmd',
    'tools/webview2_source_role_editor_native/smoke_r42ds_archive_source_roles_webview2.cmd',
    'tools/webview2_source_role_editor_native/probe_r42ds_archive_source_roles_webview2.cmd',
    'tools/webview2_source_role_editor_native/probe_r42ds_archive_source_roles_webview2.py',
    'tools/webview2_source_role_editor_native/build_r42ds_archive_source_roles_webview2_zip.cmd',
    'tools/webview2_source_role_editor_native/build_r42ds_archive_source_roles_webview2_zip.py',
    'tools/webview2_source_role_editor_native/make_r42ds_active_archive_source_roles_upload_zip.cmd',
    'tools/webview2_source_role_editor_native/make_r42ds_active_archive_source_roles_upload_zip.py',
]


def add_file(z: zipfile.ZipFile, root: Path, rel: str, arc_prefix: str = 'project') -> None:
    p = root / rel
    if p.is_file():
        z.write(p, f'{arc_prefix}/{rel}'.replace('\\', '/'))


def main() -> int:
    root = Path.cwd()
    out = root / 'profile_media_live_captures' / 'r42ds_archive_source_roles_webview2'
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_path = out / f'r42ds_archive_source_roles_webview2_{stamp}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in PROJECT_FILES:
            add_file(z, root, rel)
        latest = sorted([p for p in out.glob('probe_*') if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        for d in latest:
            for p in d.rglob('*'):
                if p.is_file() and p.stat().st_size <= 3_000_000:
                    z.write(p, f'_r42ds_probe_outputs/{d.name}/{p.relative_to(d).as_posix()}')
    downloads = Path(os.environ.get('USERPROFILE', '')) / 'Downloads'
    if downloads.is_dir():
        shutil.copy2(zip_path, downloads / zip_path.name)
        print('[DONE] Copied ZIP to Downloads:', downloads / zip_path.name)
    print('[DONE] Created ZIP:', zip_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
