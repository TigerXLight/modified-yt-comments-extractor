# V75S — Profile/media profile intake pack

V75S adds guarded profile-record intake for the Profile/Media Database mode.

It preserves the corrected folder model:

```text
Database/
  Profiles/        <- global/header Profiles collection across cases

[Case Folder]/
  Profiles/        <- profile information extracted from this case only
  People/
  Sources/
    Articles/
    Social Media/
      Offline/
      Online/
    Internal Media/
  Reference Extants/
```

## What it adds

- `profile_media_profile_intake.py`
- `profile_media_profile_intake_test.py`
- `tools/run_profile_media_profile_intake_cli_v75s.py`

The intake parser accepts the user's profile text structure:

```text
Name: xxxxx
Date: [Date]
Text: [Text]
Identifiers:
Address: [Computer local location address]
Source: [Name of source page]
```

and writes planned or confirmed records to both levels:

```text
Database/Profiles/[Name]/profile_record.json
Database/Profiles/[Name]/profile_record.txt
Cases/[Case]/Profiles/[Name]/profile_record.json
Cases/[Case]/Profiles/[Name]/profile_record.txt
```

## Safety rules

Default execution is dry-run. No files or folders are written unless the caller passes:

```text
--execute --confirm-write WRITE_PROFILE_RECORDS
```

V75S does not:

- scan folders
- classify automatically
- infer sensitive identifiers
- download media
- copy media
- move folders
- rename folders

Sensitive identifiers remain source-evidenced only and weak inference is prohibited.
