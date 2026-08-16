# Profile/Media Database V76O Command Index

Status: `IMPLEMENTED`, `CLI_ONLY`, `TESTED`

## Compile

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe -m py_compile profile_media_home_source_folder_ingestion.py profile_media_home_source_folder_ingestion_test.py tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py
```

## Direct Self-Test

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_home_source_folder_ingestion_test.py
```

## Print Fixture Preview

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py --source-folder testdata\profile_media_database_v76o_home_source_folder_fixture --print-text
```

## Write Preview JSON With Confirmation

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py --source-folder testdata\profile_media_database_v76o_home_source_folder_fixture --output-json "%TEMP%\ytce_home_source_folder_preview_v76o.json" --confirm-write WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW --print-text
```

## Safe Failure Without Confirmation

This command must fail safely and write nothing:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py --source-folder testdata\profile_media_database_v76o_home_source_folder_fixture --output-json "%TEMP%\ytce_home_source_folder_preview_v76o_blocked.json" --print-text
```

Expected write status:

`blocked_confirmation_required`

## Git Hygiene

```cmd
git diff --check
git diff --stat
git status --short
```

## Suggested Commit

```cmd
git add profile_media_home_source_folder_ingestion.py profile_media_home_source_folder_ingestion_test.py tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py PROFILE_MEDIA_DATABASE_V76O_HOME_SOURCE_FOLDER_INGESTION.md PROFILE_MEDIA_DATABASE_V76O_COMMAND_INDEX.md testdata\profile_media_database_v76o_home_source_folder_fixture testdata\profile_media_database_v76o_home_source_folder_ingestion_acceptance_matrix.json && git commit -m "Add HOME source folder ingestion preview"
```
