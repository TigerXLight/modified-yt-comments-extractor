# Profile/Media Database V75J — Sidebar Preview Panel

V75J extends the V75I left-sidebar Database toggle with a small preview panel that is visible only when Database mode is on.

## Preserved hierarchy

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

## Guardrails

The preview is a UI-only panel. It does not:

- scan folders;
- create folders;
- move folders;
- rename folders;
- copy files;
- classify records;
- infer sensitive identifiers.

## Purpose

This patch makes the Database toggle visible and understandable before the later live Database tree browser is connected to stored manifests.
