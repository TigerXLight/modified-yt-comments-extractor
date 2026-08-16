# V75K Profile/Media Sidebar View-Model Preview Bridge

V75K changes the Database sidebar preview from a hard-coded text block into a UI rendering of a tiny in-memory `ProfileMediaDatabaseManifest` processed through the V75H view model.

## Preserved hierarchy

```text
Database/
  Profiles/

Case Folder/
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

## Intent

The sidebar preview should now reflect the same manifest/tree logic used by the Profile/Media database layer. This avoids UI-only hierarchy drift, such as showing `Articles`, `Social Media`, `Offline`, `Online`, or `Internal Media` at the wrong level.

## Safety boundaries

V75K remains preview-only. It does not:

- scan folders
- create folders
- move folders
- rename folders
- copy files
- classify media
- infer sensitive identifiers

Sensitive identifiers remain source-evidenced only.
