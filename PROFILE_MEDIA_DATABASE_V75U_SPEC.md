# V75U Profile/Media Case Materialize Pack

V75U adds an explicit materialization layer for the Profile/Media Database mode.
It combines the guarded workspace, source-intake, profile-intake, and case-manifest layers into one operation.

## Default behaviour

The default is a dry-run. It does not create folders or write files unless the caller passes both:

```text
--execute --confirm-materialize MATERIALIZE_PROFILE_MEDIA_CASE
```

## Allowed only with explicit confirmation

With the confirmation phrase present, V75U may create the known Database/case folder layout and write JSON/TXT metadata records:

```text
Database/
  Profiles/
  Cases/
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
      case_manifest.json
      case_manifest.txt
```

## Still prohibited

V75U still performs no folder scan, no folder move, no folder rename, no file copy, no media download, no automatic classification, and no sensitive identifier inference.

Sensitive identifiers remain source-evidenced only.
