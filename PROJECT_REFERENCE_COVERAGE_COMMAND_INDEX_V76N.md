# Project Reference Coverage Command Index V76N

Audit date: 2026-08-16

## Start Commands

```cmd
cd /d "T:\References\to go\Media\tools\Modified YouTube comment extractor"
git status --short
git log -10 --oneline
```

Observed start state for this patch:

- Branch: `v2.6.0-asr-engines`
- HEAD: `5af82d1 Document current project capabilities and functions`
- Untracked: `external_reference_sources_20260816_article_extraction/`
- `external_reference_sources_20260814_234822` is present but not tracked by git.

## Audit Commands Used

```cmd
git ls-files
dir /b external_reference_sources_20260814_234822
type external_reference_sources_20260814_234822\Folder_Hierarchy.txt > nul
dir /b external_reference_sources_20260814_234822\01_local_browser_extension_archives
dir /b external_reference_sources_20260814_234822\02_high_priority_source_refs
dir /b external_reference_sources_20260814_234822\03_lower_priority_media_refs
dir /b external_reference_sources_20260814_234822\04_extra_source_refs
dir /b external_reference_sources_20260816_article_extraction
```

The broad tracked-source search was run with PowerShell/Select-String to avoid flooding stdout:

```cmd
powershell -NoProfile -ExecutionPolicy Bypass -Command "$files = git ls-files *.py tools/*.py *.md testdata/*.json; $matches = Select-String -Path $files -Pattern 'GoFullPage','PageCap','screenshot','capture','archive','offline','warc','har','viewer','MSN','twitter','x.com','timeline','cursor','media download','video downloader','x-article-exporter','web-exporter','metadata_parser','trafilatura','newspaper','source.txt','rtf','primary','secondary','tertiary','internal','profile_media','HOME','materialize','batch' -CaseSensitive:$false; $unique = $matches | Select-Object -ExpandProperty Path -Unique; 'MATCH_COUNT=' + $matches.Count; 'MATCHED_FILE_COUNT=' + (($unique | Measure-Object).Count)"
```

Observed summary:

- `MATCH_COUNT=56686`
- `MATCHED_FILE_COUNT=3082`

## Validation Commands

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe -m py_compile external_reference_coverage_audit_v76n_test.py tools\run_external_reference_coverage_audit_cli_v76n.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe external_reference_coverage_audit_v76n_test.py
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_external_reference_coverage_audit_cli_v76n.py --print-text
git diff --check
git diff --stat
git status --short
```

## Re-Run Audit CLI

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_external_reference_coverage_audit_cli_v76n.py --print-text
```

JSON mode:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe tools\run_external_reference_coverage_audit_cli_v76n.py --json
```

## Suggested Commit Command

```cmd
git add EXTERNAL_REFERENCE_SOURCE_COVERAGE_AUDIT_V76N.md SCREENSHOT_ARCHIVE_REFERENCE_COVERAGE_V76N.md TWITTER_X_REFERENCE_COVERAGE_V76N.md ARTICLE_EXTRACTION_REFERENCE_COVERAGE_V76N.md PROFILE_MEDIA_SOURCE_WORKFLOW_REFERENCE_GAPS_V76N.md PROJECT_REFERENCE_COVERAGE_COMMAND_INDEX_V76N.md tools/run_external_reference_coverage_audit_cli_v76n.py external_reference_coverage_audit_v76n_test.py testdata/external_reference_coverage_v76n_acceptance_matrix.json && git commit -m "Audit external reference source coverage"
```

Do not add:

```cmd
external_reference_sources_20260814_234822
external_reference_sources_20260816_article_extraction
```

