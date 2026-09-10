# R42FQ source-row icon marker compatibility

Repairs the restored `main_source_resource_ui_test.py` after the R42FP restore.

The restored test still asserted mojibake versions of the compact source-row icon glyphs. The production code now uses the real glyphs and explicit marker comments:

- image/source resource icon: `▧` / `source_row_resource_image_icon_expected_by_ui_test`
- media icon: `▶` / `source_row_resource_media_icon_expected_by_ui_test`
- remove icon: `×` / `source_row_remove_button_text_expected_by_ui_test`

This is a test-only compatibility repair. It does not change production runtime files.
