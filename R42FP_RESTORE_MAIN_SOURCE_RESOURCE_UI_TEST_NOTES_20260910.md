# R42FP restore main_source_resource_ui_test.py

Restores `main_source_resource_ui_test.py` from the user-provided R42FN debug ZIP and applies test-only R42D marker compatibility.

Reason: the previous R42FO inline command used an illegal Python `newline` value and could truncate the file before the test runner executed.

Production runtime files are not changed by this patch.
