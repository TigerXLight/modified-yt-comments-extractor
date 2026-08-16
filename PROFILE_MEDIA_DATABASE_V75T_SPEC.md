# V75T — Profile/media case manifest pack

V75T adds a guarded case-level manifest that links planned case workspace,
source-intake, and profile-intake records.

## Structure preserved

```text
Database/
  Profiles/        # global/header profiles across cases

Cases/[Case]/
  Profiles/        # case-local profile information only
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
  case_manifest.json
  case_manifest.txt
```

## Safety properties

The default is dry-run.  V75T does not scan folders, move folders, rename
folders, copy media, download media, classify automatically, or infer sensitive
identifiers.

Real manifest writing requires:

```text
--execute --confirm-write WRITE_CASE_MANIFEST
```

The case root must already exist.  This prevents the case manifest writer from
silently creating a case workspace.

## Purpose

The manifest is a reviewable index.  It records which source records and profile
records are expected to belong to a case, while preserving source role, claim
basis, source-chain gap, disputed framing, current/historical/undated status,
and source-evidenced sensitive-identifier rules.

## Workspace preview correction

V75T also hardens the case workspace text renderer so the physical `Cases`
parent is visible:

```text
Database [database_root]
  Profiles [global_profiles]
  Cases [cases]
    Example Case [case]
      Profiles [case_profiles]
      People [people]
      Sources [sources]
        Articles [articles]
        Social Media [social_media]
          Offline [social_media_offline]
          Online [social_media_online]
        Internal Media [internal_media]
      Reference Extants [reference_extants]
```
