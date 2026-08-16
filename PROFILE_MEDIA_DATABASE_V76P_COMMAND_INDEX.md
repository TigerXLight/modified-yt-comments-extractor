# Profile/Media Database V76P Command Index

## Compile

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe -m py_compile profile_media_home_source_folder_ingestion.py profile_media_home_source_folder_ingestion_test.py profile_media_source_segment_analysis.py profile_media_source_segment_analysis_test.py profile_media_social_video_provenance.py profile_media_social_video_provenance_test.py tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py
```

## Direct Tests

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_source_segment_analysis_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_social_video_provenance_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_home_source_folder_ingestion_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe profile_media_database_workbench_panel_test.py
```

## Print Preview

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py --source-folder testdata\profile_media_database_v76o_home_source_folder_fixture --print-text
```

## Confirmed Preview Write

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_home_source_folder_ingestion_cli_v76o.py --source-folder testdata\profile_media_database_v76o_home_source_folder_fixture --output-json "%TEMP%\ytce_home_source_folder_preview_v76p.json" --confirm-write WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW --print-text
```

## Hygiene

```cmd
git diff --check
git diff --stat
git status --short
```

## Suggested Commit

```cmd
git add profile_media_source_segment_analysis.py profile_media_source_segment_analysis_test.py profile_media_social_video_provenance.py profile_media_social_video_provenance_test.py profile_media_home_source_folder_ingestion.py profile_media_home_source_folder_ingestion_test.py profile_media_database_workbench_panel.py profile_media_database_workbench_panel_test.py PROFILE_MEDIA_DATABASE_V76O_HOME_SOURCE_FOLDER_INGESTION.md PROFILE_MEDIA_DATABASE_V76P_IMPLEMENTATION_CLOSEOUT.md PROFILE_MEDIA_DATABASE_V76P_COMMAND_INDEX.md testdata\profile_media_database_v76o_home_source_folder_fixture testdata\profile_media_database_v76p_implementation_closeout_acceptance_matrix.json && git commit -m "Close out profile media database source workflow"
```
