from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional


REPO_OWNER = "TigerXLight"
REPO_NAME = "modified-yt-comments-extractor"
RELEASES_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"


@dataclass
class UpdateCheckResult:
    ok: bool
    update_available: bool = False
    current_version: str = ""
    latest_version: str = ""
    release_url: str = RELEASES_URL
    error: str = ""


def _normalise_version(version: str) -> tuple[int, ...]:
    """
    Converts versions like 'v1.2.3' or '1.2.3' into comparable tuples.
    Non-number suffixes are ignored.
    """
    version = (version or "").strip().lower()
    if version.startswith("v"):
        version = version[1:]

    parts = []
    for piece in version.split("."):
        digits = ""
        for ch in piece:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)

    while len(parts) < 3:
        parts.append(0)

    return tuple(parts[:3])


def check_for_updates(current_version: str, timeout: int = 8) -> UpdateCheckResult:
    """
    Checks GitHub Releases for the latest version.
    Does not auto-download or auto-install anything.
    """
    try:
        request = urllib.request.Request(
            LATEST_RELEASE_API,
            headers={
                "User-Agent": f"{REPO_NAME}-update-checker",
                "Accept": "application/vnd.github+json",
            },
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        latest_version = payload.get("tag_name", "").strip()
        release_url = payload.get("html_url", RELEASES_URL)

        update_available = (
            _normalise_version(latest_version) > _normalise_version(current_version)
        )

        return UpdateCheckResult(
            ok=True,
            update_available=update_available,
            current_version=current_version,
            latest_version=latest_version,
            release_url=release_url,
        )

    except urllib.error.HTTPError as e:
        return UpdateCheckResult(
            ok=False,
            current_version=current_version,
            error=f"GitHub returned HTTP error {e.code}.",
        )

    except urllib.error.URLError as e:
        return UpdateCheckResult(
            ok=False,
            current_version=current_version,
            error=f"Could not connect to GitHub: {e.reason}",
        )

    except Exception as e:
        return UpdateCheckResult(
            ok=False,
            current_version=current_version,
            error=str(e),
        )