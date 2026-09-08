@echo off
setlocal
cd /d "%~dp0..\.."
echo [R42EI] Running main-app file converter integration smoke tests. No GUI/WebView2/archive.ph/network.
call tools\profile_media_file_converter\_r42ei_python.cmd -m py_compile main.py profile_media_file_converter_r42eh.py profile_media_file_converter_r42eg.py profile_media_file_converter_r42eh_test.py || exit /b 1
call tools\profile_media_file_converter\_r42ei_python.cmd profile_media_file_converter_r42eh_test.py || exit /b 1
echo [R42EI] Checking main-app integration markers...
call tools\profile_media_file_converter\_r42ei_python.cmd -c "from pathlib import Path; import json; s=Path('main.py').read_text(encoding='utf-8', errors='replace'); checks={'main_app_file_converter_panel':'def _create_file_converter_section' in s,'files_row_convert_action':'def _file_converter_add_session_file' in s and 'FILES row' in s,'active_media_convert_action':'def _file_converter_add_active_media_file' in s and 'Add active media' in s,'image_window_convert_action':'_download_webpage_image_resource_ids_to_files_and_convert' in s and 'Convert selected' in s,'video_audio_window_convert_action':'_download_webpage_video_audio_resource_ids_to_files_and_convert' in s and 'download-convert-selected' in s,'helper_namespace_is_profile_media':'tools/profile_media_file_converter' in str(Path('tools/profile_media_file_converter/smoke_r42ei_file_converter_main_app_integration.cmd').as_posix())}; print(json.dumps(checks, indent=2)); raise SystemExit(0 if all(checks.values()) else 1)" || exit /b 1
echo [DONE] R42EI smoke passed.
