# V75V Profile/Media Case Batch Pack

V75V adds a batch JSON intake layer for the Profile/Media Database mode.

It lets one case payload contain multiple Sources and multiple Profiles, while reusing the guarded V75U materialization layer.

## Batch JSON shape

```json
{
  "database_root": "T:/Example Database",
  "case_title": "Example Case",
  "sources": [
    {
      "source_page": "BelfastLive",
      "source_title": "June 2026 - Example Article",
      "source_bucket": "Articles",
      "source_role": "TERTIARY_PROPAGATED_SOURCE",
      "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
      "currentness_status": "CURRENT",
      "source_chain_gap": true
    }
  ],
  "profiles": [
    {
      "profile_text": "Name: Example Person\nDate: 2026-06-05\nText: ...\nIdentifiers:\nAddress: ...\nSource: BelfastLive",
      "source_bucket": "Articles",
      "source_role": "TERTIARY_PROPAGATED_SOURCE",
      "claim_basis": "AGENCY_OR_OUTSIDE_RETELLING",
      "currentness_status": "CURRENT"
    }
  ]
}
```

## Safety boundary

Default is dry-run. Execution requires:

```text
--execute --confirm-batch APPLY_PROFILE_MEDIA_BATCH_CASE
```

The batch layer blocks requested scan/move/rename/copy/download/automatic-classification/sensitive-inference operations.

V75V may create only known Database/Profiles/Cases case folders and JSON/TXT metadata records when explicitly confirmed.

It still does not:

- scan folders
- move folders
- rename folders
- copy media
- download media
- classify automatically
- infer sensitive identifiers
