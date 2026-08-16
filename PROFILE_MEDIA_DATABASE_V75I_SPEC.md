# Profile/media Database V75I - sidebar toggle

V75I wires the previously added V75H FILES/DATABASE view model into the main left sidebar as a minimal mode toggle.

## Placement

The Database toggle is inserted after the EXPORT section and directly before the existing FILES section:

```text
EXPORT
DATABASE
  On / Off
  Mode: FILES | Mode: DATABASE - preview only
FILES
```

This preserves the user-requested rule that Database mode is exposed on the left above FILES.

## Safety boundary

The toggle is view-state only. It does not:

- scan folders
- create folders
- rename folders
- move folders
- copy media
- classify records
- infer sensitive identifiers

Switching to DATABASE mode records only the local UI state and shows a preview-only status string. Real folder operations remain guarded by the V75D/V75E review and approval model.

## Source terminology

The toggle exposes Database mode without changing the folder model:

```text
Database/
  Profiles/        # global/header profile collection

[Case Folder]/
  Profiles/        # case-limited extracted profiles
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```
