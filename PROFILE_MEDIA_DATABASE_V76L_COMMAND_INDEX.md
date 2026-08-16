# V76L Command Index

Run the adapter against the included fixture:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_article_extraction_cli_v76l.py --html-file testdata\profile_media_database_v76l_article_fixture.html --source-url https://example.test/news/2026/jun/21/source-fixture --print-text --print-json
```

Run with the optional downloaded reference repositories:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_article_extraction_cli_v76l.py --html-file testdata\profile_media_database_v76l_article_fixture.html --reference-root external_reference_sources_20260816_article_extraction --print-text
```

Write a guarded standalone source preview:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_profile_media_article_extraction_cli_v76l.py --html-file testdata\profile_media_database_v76l_article_fixture.html --output-json "%TEMP%\ytce_profile_media_article_source_preview_v76l.json" --confirm-write WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW --print-text
```
