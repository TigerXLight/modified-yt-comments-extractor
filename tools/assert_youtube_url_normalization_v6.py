from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from youtube_media_download_backend import normalize_media_source_url_arg_strict

NESTED = r"[[https://www.youtube.com/watch?v=VIDEO\_ID\](https://www.youtube.com/watch?v=VIDEO\_ID)](https://www.youtube.com/watch?v=VIDEO_ID]\(https://www.youtube.com/watch?v=VIDEO_ID\))"
SAMPLES = {
    r"[https://www.youtube.com/watch?v=VIDEO\_ID](https://www.youtube.com/watch?v=VIDEO_ID)": "https://www.youtube.com/watch?v=VIDEO_ID",
    NESTED: "https://www.youtube.com/watch?v=VIDEO_ID",
    "https://www.youtube.com/watch?v=VIDEO_ID": "https://www.youtube.com/watch?v=VIDEO_ID",
    "URL: https://www.youtube.com/watch?v=abc123": "https://www.youtube.com/watch?v=abc123",
}

for raw, expected in SAMPLES.items():
    actual = normalize_media_source_url_arg_strict(raw)
    print(f"NORMALIZED_URL={actual}")
    if actual != expected:
        raise SystemExit(f"URL normalization failed: raw={raw!r} expected={expected!r} actual={actual!r}")

with tempfile.TemporaryDirectory() as tmp:
    completed = subprocess.run(
        [
            sys.executable,
            "youtube_media_download_backend_cli.py",
            "--source-url",
            NESTED,
            "--output-dir",
            tmp,
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    expected_line = "YOUTUBE_MEDIA_SOURCE_URL=https://www.youtube.com/watch?v=VIDEO_ID"
    if expected_line not in completed.stdout:
        raise SystemExit("CLI did not print normalized raw source URL. stdout was:\n" + completed.stdout)

    plan_path = Path(tmp) / "youtube-media-download-plan.json"
    data = json.loads(plan_path.read_text(encoding="utf-8"))
    if data.get("source_url") != "https://www.youtube.com/watch?v=VIDEO_ID":
        raise SystemExit(f"Plan source_url was not normalized: {data.get('source_url')!r}")

print("YOUTUBE_MEDIA_URL_NORMALIZATION_V6_OK")
