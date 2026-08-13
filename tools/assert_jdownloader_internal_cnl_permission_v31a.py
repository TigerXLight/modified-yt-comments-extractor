from pathlib import Path

cnl = Path("jdownloader_internal_cnl.py").read_text(encoding="utf-8")
required = [
    'CNL_PERMISSION_BYPASS_REFERER = f"{JD_BASE_URL}/flashgot"',
    '"Referer": CNL_PERMISSION_BYPASS_REFERER',
    '"Origin": JD_BASE_URL',
    'ordered_routes = tuple(routes or ("/flashgot", "/flash/add"))',
    'if body.startswith("failed"):',
]
missing = [item for item in required if item not in cnl]
if missing:
    raise SystemExit("V31A CNL permission patch missing markers: " + repr(missing))
if 'ordered_routes = tuple(routes or ("/flash/add", "/flashgot", "/flash/addcrypted2"))' in cnl:
    raise SystemExit("Old default route order with addcrypted2 is still present.")
wrapper = Path("tools/jdownloader/RUN_INTERNAL_JDOWNLOADER_YOUTUBE_ID_REAL_TEST.cmd")
if not wrapper.is_file():
    raise SystemExit("Missing video-ID real-test wrapper.")
text = wrapper.read_text(encoding="utf-8")
if "jdownloader_internal_job.py" not in text:
    raise SystemExit("Video-ID wrapper does not call the internal JDownloader job runner.")
print("assert_jdownloader_internal_cnl_permission_v31a OK")
