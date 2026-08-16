# V75G Profile/Media Database Hierarchy-Correct Tree Preview

V75G corrects the Database-mode tree view so the rendered preview mirrors the intended physical case folder model:

```text
Database/
  Profiles/              # global/header profile collection across cases

Case Folder/
  Profiles/              # case-limited extracted profiles
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```

## Scope

V75G is still a planning/read-write helper layer only. It does not:

- scan folders
- create case folders
- move folders
- rename folders
- copy files
- classify automatically
- infer sensitive identifiers
- fetch sources
- run browser automation

## Tree row changes

`ProfileMediaTreeRow` now carries:

- `parent_row_id`
- `display_order`

These fields allow the UI layer to preserve explicit parent/child relationships instead of relying only on label text.

## Rendered hierarchy

The text preview now nests containers correctly:

```text
Database Root [database_root]
  Profiles [global_profiles]
    Example Person [profile]
  Example Case [case]
    Profiles [case_profiles]
      Example Person [case_profile_record]
    People [people]
    Sources [sources]
      Articles [articles]
        Example Article [media_source]
      Social Media [social_media]
        Offline [social_media_offline]
        Online [social_media_online]
      Internal Media [internal_media]
    Reference Extants [reference_extants]
```

Media-source rows are placed under their actual source bucket:

- `Articles` sources under `Sources/Articles`
- `Social Media/Offline` sources under `Sources/Social Media/Offline`
- `Social Media/Online` sources under `Sources/Social Media/Online`
- `Internal Media` sources under `Sources/Internal Media`
- `Reference Extants` sources under `Reference Extants`

## Safety

The database manifest remains the planning truth. Folder movement remains review-gated through the V75D/V75E review and folder-operation layer.
