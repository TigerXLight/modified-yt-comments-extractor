# V76A Profile/Media Database Workbench Pack

V76A is the first larger Profile/Media Database pack after V75Z.  It combines
multiple related UI-neutral pieces into one tested patch instead of splitting
one small feature into many separate zips.

## Purpose

The pack prepares the future **main Database mode workbench** while preserving
the sidebar rule:

```text
DATABASE
  square On / Off toggle only
FILES
```

It does not reintroduce a sidebar preview and it does not add a sidebar filter.
The new workbench state is for the main content area once Database mode is on.

## Added files

```text
profile_media_database_dashboard.py
profile_media_database_dashboard_test.py
profile_media_database_navigation.py
profile_media_database_navigation_test.py
profile_media_database_workbench.py
profile_media_database_workbench_test.py
tools/run_profile_media_database_workbench_cli_v76a.py
PROFILE_MEDIA_DATABASE_V76A_SPEC.md
```

## Dashboard model

The dashboard summarizes an explicit batch-driven index into:

```text
- case count
- source count
- profile row count
- unique global profile count
- source-chain gap count
- disputed-framing count
- unknown source-role count
- parser-warning count
- source bucket facets
- source role facets
- claim basis facets
- currentness facets
- profile source bucket facets
- manual review lanes
```

The dashboard is read-only and consumes only explicit batch JSON paths or
already-loaded payloads.

## Navigation model

The navigation model creates UI-neutral targets for:

```text
case rows
source rows
profile rows
```

Each target contains:

```text
target_type
title
case_title
local_address
breadcrumb
source_bucket
source_role
claim_basis
source_page
metadata
```

It is a target/index model only.  It does not open files or folders.

## Workbench bundle

The workbench combines:

```text
- Database session snapshot
- Database mode view
- Dashboard
- Navigation targets
- Review report
- Default saved views
- Guarded export plan
```

Default saved views are created in memory only:

```text
All Database Records
Source-chain gaps
Disputed framing
Unknown source roles
Parser warnings
```

## Export guard

Workbench export defaults to dry-run.

Real export requires:

```text
--execute-export --confirm-export EXPORT_PROFILE_MEDIA_DATABASE_WORKBENCH
```

When confirmed, it writes only JSON/TXT workbench export files.  It does not
copy media or alter case folders.

## Prohibited operations

The pack must not perform:

```text
folder scanning
folder creation, except export output folder after explicit export confirmation
folder moving
folder renaming
media copying
media downloading
automatic classification
sensitive identifier inference
sidebar preview/filter insertion
```

The test suite asserts these safety flags.

## Relationship to earlier V75 packs

V75A-V75G built the profile/media database foundation, tree, review, and folder
operation planning.  V75H-V75O built the mode-only Database sidebar toggle.
V75P-V75Y built runtime mode, case workspace planning, source/profile intake,
case manifest/materialization, batch JSON, index/search, and Database-mode view.
V75Z combined session/export/saved-view/review pieces.

V76A consolidates the next layer into a single larger workbench pack.
