from pathlib import Path

cnl = Path("jdownloader_internal_cnl.py").read_text(encoding="utf-8")
required = [
    "def _cnl_attempt_was_sent_but_response_timed_out",
    "CNL request timed out while waiting for JD response; treating as submitted-unknown and monitoring output folder.",
    "No additional CNL routes were attempted to avoid duplicate LinkGrabber jobs.",
    '"referer": CNL_PERMISSION_BYPASS_REFERER',
    '"autoConfirm": "1"',
]
missing = [item for item in required if item not in cnl]
if missing:
    raise SystemExit("V31B fire-and-monitor patch missing markers: " + repr(missing))
print("assert_jdownloader_internal_cnl_fire_monitor_v31b OK")
