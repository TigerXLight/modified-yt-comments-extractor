# Profile Media Database V75D - Review Queue and Audit Planning

V75D adds a review/audit layer on top of the V75A-V75C profile/media database foundation.

## Scope

V75D is still a dry-run planning layer only. It does not create folders, copy files, move files, rename folders, scan folders, classify automatically, fetch sources, download media, or infer sensitive identifiers.

## Added concepts

- `ProfileMediaReviewItem` records a pending review for folder move/path-change/identifier/source-claim decisions.
- `ProfileMediaReviewQueue` groups review items and exposes pending/approved/rejected counts.
- `ProfileMediaAuditEvent` records why a review decision or path change was proposed.
- Review decisions can be recorded without performing any filesystem action.

## Folder move philosophy

The database/profile manifest remains the planning and audit controller. Folders may later be renamed or moved, but only through a separate confirmed operation. V75D only prepares the review records that explain the old path, proposed new path, reason, source basis, source role, claim basis, and whether sensitive review is required.

## Case structure preserved

The design preserves the user-specified split:

```text
Database/
  Profiles/              # global/header Profiles collection across cases

[Case Folder]/
  Profiles/              # profiles extracted from this case only
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```

`Source: [Name of source page]` may refer to Articles, Social Media Online/Offline, or Internal Media.
