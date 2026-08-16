# V75Z Profile/Media Database session + export pack

V75Z is a larger combined pack for the Profile/Media Database mode workstream. It connects the existing database pieces into one UI-neutral runtime layer that the future main Database screen can use.

## Scope

This pack adds:

- `profile_media_database_session.py`
- `profile_media_database_session_test.py`
- `tools/run_profile_media_database_session_cli_v75z.py`
- this specification file

It does not change the mode-only sidebar toggle. The sidebar remains:

```text
DATABASE
  On / Off
FILES
```

The Database-mode content belongs in the main workspace, not in the sidebar.

## Purpose

Earlier packs created the core layers:

- V75V: batch case JSON input
- V75W: read-only database index
- V75X: read-only database search
- V75Y: UI-neutral Database mode view

V75Z adds a session/controller layer around those parts:

```text
explicit batch JSON files
  -> read-only index
  -> read-only search
  -> Database mode view
  -> Database session snapshot
  -> optional guarded export
```

## Session config

A session config stores:

```text
database_root
batch_json_files[]
mode = FILES / DATABASE
profile_name
case_title
source_bucket
source_role
claim_basis
currentness_status
text
source_chain_gap
disputed_framing
has_parser_warnings
limit
```

The session config can be loaded from or written to JSON when explicitly requested. It does not scan directories to discover cases or sources.

## Session snapshot

The snapshot records:

```text
mode
runtime state
batch JSON files
index counts
matched source/profile counts
Database-mode view payload
safety flags
warnings
```

The snapshot is suitable for a future main Database-mode UI panel.

## Export planning

V75Z adds guarded export planning for a Database-mode session/view.

Default behavior is dry-run:

```text
status = planned_dry_run
file_write_performed = false
```

Real export writes require:

```text
--execute-export --confirm-export EXPORT_PROFILE_MEDIA_DATABASE_VIEW
```

The export writes only metadata/view files to the requested export directory:

```text
database_mode_view.json
database_mode_view.txt
database_mode_view_summary.json
```

The export is not a case materialization operation. It does not create case folder structures, move folders, rename folders, copy media, download media, or classify automatically.

## Hard safety guarantees

V75Z preserves these flags in normal read-only/session mode:

```text
folder_scan_performed = false
folder_creation_performed = false
folder_move_performed = false
folder_rename_performed = false
file_copy_performed = false
file_write_performed = false
media_download_performed = false
automatic_classification_performed = false
sensitive_identifier_inference_performed = false
```

When guarded export execution is explicitly confirmed, only these flags may become true:

```text
folder_creation_performed = true
file_write_performed = true
```

because the export directory is created and metadata export files are written. The export still must not scan folders, move folders, rename folders, copy media, download media, classify automatically, or infer sensitive identifiers.

## CLI examples

Dry-run/read-only session snapshot:

```cmd
python tools\run_profile_media_database_session_cli_v75z.py --write-demo-batch "%TEMP%\ytce_profile_media_batch_v75z.json" --database-root "%TEMP%\ytce_profile_media_db_v75z_demo" --case-title "Example Case" --profile-name "Second" --print-session
```

Dry-run export plan:

```cmd
python tools\run_profile_media_database_session_cli_v75z.py --write-demo-batch "%TEMP%\ytce_profile_media_batch_v75z.json" --database-root "%TEMP%\ytce_profile_media_db_v75z_demo" --case-title "Example Case" --source-chain-gap true --export-dir "%TEMP%\ytce_profile_media_export_v75z"
```

Confirmed metadata export:

```cmd
python tools\run_profile_media_database_session_cli_v75z.py --batch-json "%TEMP%\ytce_profile_media_batch_v75z.json" --source-chain-gap true --export-dir "%TEMP%\ytce_profile_media_export_v75z" --execute-export --confirm-export EXPORT_PROFILE_MEDIA_DATABASE_VIEW
```

## User model preserved

The Database remains:

```text
Database/
  Profiles/        <- global/header Profiles collection across cases
  Cases/
    [Case Folder]/
      Profiles/    <- case-limited profile information extracted from that case only
      People/
      Sources/
        Articles/
        Social Media/
          Offline/
          Online/
        Internal Media/
      Reference Extants/
```

`Source: [Name of source page]` can point to Articles, Social Media/Online, Social Media/Offline, or Internal Media, depending on the source bucket used by the batch/profile/source records.

## Larger-pack additions

This pack also includes two supporting layers so later GUI work can move faster with fewer back-and-forth patches.

### Saved views

`profile_media_database_saved_views.py` stores named Database-mode query presets. A saved view can preserve:

```text
batch_json_files
mode
profile_name
case_title
source_bucket
source_role
claim_basis
currentness_status
text
source_chain_gap
disputed_framing
has_parser_warnings
limit
```

Saved views are user-controlled JSON metadata. They do not discover or scan folders.

### Review report

`profile_media_database_review_report.py` builds a read-only review report from the current Database session snapshot. It highlights:

```text
source-chain gaps
disputed framing
unknown source roles
profile parser warnings
session warnings
```

This matches the project rule that uncertain source chains and disputed framing must be preserved for review rather than collapsed into a single automated conclusion.

## Files added by V75Z

```text
profile_media_database_session.py
profile_media_database_session_test.py
profile_media_database_saved_views.py
profile_media_database_saved_views_test.py
profile_media_database_review_report.py
profile_media_database_review_report_test.py
tools/run_profile_media_database_session_cli_v75z.py
PROFILE_MEDIA_DATABASE_V75Z_SPEC.md
```

## Included complex fixture

V75Z includes:

```text
testdata/profile_media_database_v75z_complex_batch_fixture.json
```

This is a synthetic fixture with multiple source buckets, source roles, claim bases, disputed-framing flags, source-chain gap flags, and profile records. It exists to support larger regression packs and future Database-mode UI development without relying on real case data.
