# Profile Media Database V75B

V75B extends the V75A local-only foundation with source/container import planning.
It preserves the distinction between the global/header `Database/Profiles` folder
and the case-local `[Case Folder]/Profiles` folder.

## Global and case profile folders

```text
Database/
  Profiles/              # global/header Profiles collection across cases

[Case Folder]/
  Profiles/              # case-limited profiles extracted from this case only
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```

## Source containers

`Source: [Name of source page]` may refer to any case source container:

- `Sources/Articles`
- `Sources/Social Media/Online`
- `Sources/Social Media/Offline`
- `Sources/Internal Media`

External media is represented by the non-internal source containers. `Internal
Media` is reserved for media created or obtained by the case creator. The module
plans where a source should live, but it does not copy, move, rename, or create
files.

## Source-claim evaluation

Each planned source can carry a source-claim evaluation record using the user's
terminology:

- primary / secondary / tertiary source role
- self-authored, witness, family/authority, agency/outside retelling, identity,
  appearance, user note, or unknown claim basis
- current / historical / undated / unknown status
- disputed framing and context-dispute notes
- source-chain gap
- confidence / verification notes
- family-or-authority claim basis
- identity claim basis
- appearance claim basis
- corroboration notes

Sensitive identifiers remain source-evidenced only. V75B does not infer religion,
ethnicity, skin colour, associations, or other sensitive identity claims from
names, clothing, appearance, or weak context.

## Safety boundary

V75B is still a planning layer. It does not scan folders, create folders, copy
files, move files, rename folders, classify automatically, fetch sources, or wire
GUI controls.
