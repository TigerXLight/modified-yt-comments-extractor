# V75Q — Profile/media case workspace pack

V75Q adds an explicit, guarded case-workspace folder planner/creator for the Profile/Media Database mode.

## Folder shape

```text
Database/
  Profiles/

[Case Folder]/
  Profiles/
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```

## Safety rules

Default CLI use is dry-run. It does not create folders. Real folder creation requires both:

```text
--execute --confirm-create CREATE_CASE_WORKSPACE
```

V75Q does not scan folders, move folders, rename folders, copy files, classify records, or infer sensitive identifiers.

## Files

```text
profile_media_case_workspace.py
profile_media_case_workspace_test.py
tools/run_profile_media_case_workspace_cli_v75q.py
```
