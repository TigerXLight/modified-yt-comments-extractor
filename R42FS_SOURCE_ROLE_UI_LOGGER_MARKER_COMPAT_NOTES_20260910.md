# R42FS source-role UI logger marker compatibility

- Scope: test-only repair for main_source_resource_ui_test.py.
- Reason: the restored test expected an old exact logger.debug string for the media-filter source-role rerender path.
- Current code keeps the protected no-rebuild/yview behaviour using newer markers.
- This patch accepts the old logger marker or the newer R36J/no-rebuild/restore-yview markers.
- No production source files are changed by this patch script.
