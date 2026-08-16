# V75C Profile/Media Case Repository Path Planning

## Scope

V75C extends the V75A/V75B local profile/media database foundation with dry-run case repository path planning.

It does not create folders, copy files, move files, rename folders, scan folders, classify automatically, infer sensitive identifiers, fetch sources, or run a GUI.

## Preserved folder model

```text
Database/
  Profiles/                 # global/header Profiles collection across cases

[Case Folder]/
  Profiles/                 # case-limited profile information extracted from that case only
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```

`Source: [Name of source page]` may refer to media in `Sources/Articles`, `Sources/Social Media/Online`, `Sources/Social Media/Offline`, or `Sources/Internal Media`.

## New concepts

- `CaseRepositoryClassification`: path-planning facets for a case.
- `CaseRepositoryPathPlan`: dry-run proposed case path plus case folder layout.
- `build_case_repository_path`: renders repository path from classification facets.
- `plan_case_repository_location`: compares current and proposed case roots and emits a review-required move plan when different.
- `build_case_record_from_repository_plan`: creates a case record from a path plan without touching the filesystem.

## Sensitive classification guard

Sensitive path buckets such as religious identity require source basis. V75C records warnings when a sensitive repository bucket is selected without source basis. It does not infer religion, ethnicity, skin colour, or associations from names or appearance.

## Move safety

All path movement is dry-run only. Folder moves/renames require later explicit review and user confirmation.
