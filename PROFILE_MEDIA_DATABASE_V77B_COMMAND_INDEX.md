# Profile/Media Database V77B Command Index

## Validation Commands

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe -m py_compile profile_media_nested_source_units_v77b.py profile_media_nested_source_units_v77b_test.py profile_media_home_source_folder_ingestion.py profile_media_home_source_folder_ingestion_test.py tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py
```

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_home_source_folder_ingestion_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_social_video_provenance_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_nested_source_units_v77b_test.py
```

## Fixture CLI

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py --source-folder "testdata\profile_media_database_v77b_gb_news_nested_case\GB NEWS" --output-json "%TEMP%\ytce_gb_news_nested_case_preview_v77b_fixture.json" --confirm-write WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW --print-text
```

## Real Extracted Case Root CLI

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py --source-folder "%TEMP%\ytce_gb_news_nested_case_v4\GB NEWS" --output-json "%TEMP%\ytce_gb_news_nested_case_preview_v77b.json" --confirm-write WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW --print-text
```

The real command requires that `%TEMP%\ytce_gb_news_nested_case_v4\GB NEWS` already exists. V77B does not unzip, download, crawl, or create that case root.

## Suggested Commit Command

```cmd
git add profile_media_nested_source_units_v77b.py profile_media_nested_source_units_v77b_test.py profile_media_home_source_folder_ingestion.py PROFILE_MEDIA_DATABASE_V77B_NESTED_SOURCE_UNIT_RECOGNITION.md PROFILE_MEDIA_DATABASE_V77B_COMMAND_INDEX.md testdata\profile_media_database_v77b_gb_news_nested_case && git commit -m "Add nested Profile Media source unit recognition"
```
