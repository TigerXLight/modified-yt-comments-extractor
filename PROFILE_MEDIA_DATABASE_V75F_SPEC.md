# Profile/Media Database V75F — Manifest persistence and tree preview

V75F adds a lightweight persistence and tree-preview layer for Database mode.

## Scope

This patch supports:

- JSON manifest writing and reading.
- Text tree preview writing.
- Lightweight `ProfileMediaTreeRow` records for a Database-mode browser.
- A dry-run CLI preview tool.

## Folder model

The folder model remains:

```text
Database/
  Profiles/              # global/header profile collection across cases

[Case Folder]/
  Profiles/              # case-limited profile information extracted from that case only
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

## Safety

V75F does not scan case folders, classify automatically, infer sensitive identifiers, move folders, rename folders, copy media, or create case repositories.

The only file-writing helpers are for manifest/tree output files. Parent folder creation for those output files is opt-in.
