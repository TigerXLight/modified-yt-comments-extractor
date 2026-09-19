from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import socket
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MARKER = "YTCE_R44I_REDDIT_LOGGED_IN_TARGET_ONLY_VISIBLE_SESSION"
PASS_STATUS = "PASS_R44I_REDDIT_LOGGED_IN_TARGET_ONLY_VISIBLE_SESSION"
MANUAL_MARKER = "YTCE_R44I_OLD_REDDIT_MANUAL_CURRENT_PAGE_CAPTURE"
BLOCKED_STATUS = "BLOCKED_R44I_REDDIT_LOGGED_IN_TARGET_ONLY_VISIBLE_SESSION"
DEFAULT_TARGET_URL = "https://en.reddit.com/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/?sort=old&screen_view_count=1&limit=500&ext-referrer=DIRECT"
DEFAULT_ACCOUNT_HANDLE = "r_EdSheeran"


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _plain_url(value: str) -> str:
    text = str(value or "").strip().strip("<>")
    text = text.replace("&amp;", "&")
    return text


def _safe_name(value: str, fallback: str = "reddit_target") -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("._-")
    return text or fallback


def _host(url: str) -> str:
    try:
        return urlsplit(url).netloc.lower()
    except Exception:
        return ""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")


def _find_default_chromium_executable() -> str:
    candidates = [
        Path.home() / "AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe",
        Path.home() / "AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright/chromium-1234/chrome-win64/chrome.exe",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return ""


def _default_user_data_dir() -> str:
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData/Local")
    return str(Path(local) / "YTCE" / "reddit_logged_in_target_only_chromium_profile")


def _is_probably_executable_dir(path_text: str) -> bool:
    path = Path(path_text)
    return path.name.lower() in {"chrome-win64", "chromium", "chrome"} and (path / "chrome.exe").is_file()


def _sanitize_current_reddit_dom_html(raw_html: str) -> str:
    """Python fallback sanitizer used for tests and emergency saved HTML.

    The live path uses browser-side DOM cloning first. This fallback avoids the
    biggest current-Reddit pollution sources before handing HTML to R44D.
    """
    html = str(raw_html or "")
    for pattern in (
        r"<aside\b.*?</aside>",
        r"<nav\b.*?</nav>",
        r"<reddit-sidebar-nav\b.*?</reddit-sidebar-nav>",
        r"<shreddit-ad-post\b.*?</shreddit-ad-post>",
        r"<auth-flow-modal\b.*?</auth-flow-modal>",
        r"<reddit-cookie-banner\b.*?</reddit-cookie-banner>",
        r"<faceplate-dialog\b.*?</faceplate-dialog>",
        r"<script\b.*?</script>",
        r"<style\b.*?</style>",
    ):
        html = re.sub(pattern, " ", html, flags=re.I | re.S)
    blocks: list[str] = []
    for tag in ("shreddit-post", "shreddit-comment", "article"):
        for match in re.finditer(rf"<{tag}\b[^>]*>.*?</{tag}>", html, flags=re.I | re.S):
            block = match.group(0)
            lower = re.sub(r"<[^>]+>", " ", block).lower()
            if any(bad in lower for bad in ("related posts", "promoted", "shop now", "accept all", "sign in with apple")):
                continue
            if "/comments/" not in block.lower() and "shreddit-comment" not in block.lower():
                continue
            blocks.append(block)

    # Old Reddit does not use shreddit-* tags. Keep the main content/comment area
    # and remove sidebars/scripts/styles instead of returning an empty DOM.
    if not blocks and _looks_like_old_reddit_thread(html, html):
        old_html = html
        for pattern in (
            r"<div[^>]+class=[\"'][^\"']*side[^\"']*[\"'][^>]*>.*?</div>",
            r"<div[^>]+id=[\"']header[\"'][^>]*>.*?</div>",
            r"<script\b.*?</script>",
            r"<style\b.*?</style>",
        ):
            old_html = re.sub(pattern, " ", old_html, flags=re.I | re.S)
        m = re.search(r"<div[^>]+class=[\"'][^\"']*content[^\"']*[\"'][^>]*>.*", old_html, flags=re.I | re.S)
        blocks = [m.group(0) if m else old_html]

    if not blocks and "/comments/" in html.lower():
        blocks = [html]
    return "<html><body>\n" + "\n".join(blocks) + "\n</body></html>"


def _blocker_status_from_text(url: str, text: str) -> tuple[str, str]:
    lower = (str(url or "") + "\n" + str(text or "")).lower()
    if "you've been blocked by network security" in lower or "you’ve been blocked by network security" in lower:
        return ("BLOCKED_REDDIT_NETWORK_SECURITY", "Reddit network security block page detected; stopped without retrying.")
    if "/login" in str(url or "").lower() or "log in to use old reddit" in lower:
        return ("BLOCKED_REDDIT_LOGIN_REQUIRED", "Reddit login page detected; stopped without credential automation.")
    return ("", "")




def _looks_like_old_reddit_thread(html: str, text: str) -> bool:
    lower = (str(html or '') + '\n' + str(text or '')).lower()
    return (
        'old reddit' in lower
        or 'all 351 comments' in lower
        or 'commentarea' in lower
        or 'submitted 3 days ago by' in lower
        or 'sorted by: old' in lower
    )


def _sanitized_html_has_target_content(html: str) -> bool:
    lower = str(html or '').lower()
    return (
        '/comments/' in lower
        or 'shreddit-comment' in lower
        or 'thing id-t1_' in lower
        or 'commentarea' in lower
        or 'all 351 comments' in lower
    )

def _run_self_test(output_root: Path) -> dict[str, Any]:
    shutil.rmtree(output_root, ignore_errors=True)
    output_root.mkdir(parents=True, exist_ok=True)
    fixture = """
<html><body>
<main>
<shreddit-post id="t3_1whbgzk"><a href="https://www.reddit.com/r/EdSheeran/comments/1whbgzk/">[ Removed by moderator ]</a><p>Main target post</p></shreddit-post>
<aside><a href="https://www.reddit.com/r/EdSheeran/comments/1wge713/related/">Related post should not survive</a><img src="https://www.redditstatic.com/shreddit/assets/right-rail/streetwear.jpg"></aside>
<shreddit-comment id="t1_pa1bbed"><a href="https://www.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1bbed/">comment permalink</a><p>Again, I think it’s completely possible that Kraft is upset...</p></shreddit-comment>
<shreddit-ad-post><img src="https://preview.redd.it/ad.jpg"><p>Shop Now</p></shreddit-ad-post>
<reddit-cookie-banner>Accept All</reddit-cookie-banner>
</main>
</body></html>
"""
    sanitized = _sanitize_current_reddit_dom_html(fixture)
    checks = [
        {"name": "target_post_survives", "status": "pass" if "1whbgzk" in sanitized else "fail"},
        {"name": "target_comment_survives", "status": "pass" if "pa1bbed" in sanitized else "fail"},
        {"name": "right_rail_related_post_removed", "status": "pass" if "1wge713" not in sanitized and "streetwear" not in sanitized else "fail"},
        {"name": "ad_and_cookie_banner_removed", "status": "pass" if "Shop Now" not in sanitized and "Accept All" not in sanitized else "fail"},
    ]
    report = {
        "marker": MARKER,
        "status": PASS_STATUS if all(c["status"] == "pass" for c in checks) else BLOCKED_STATUS,
        "schema_version": "reddit_logged_in_target_only_visible_session.r44i.v1",
        "checks": checks,
        "contract": _contract(),
        "sanitized_fixture_path": str(output_root / "sanitized_fixture.html"),
    }
    _write_text(output_root / "sanitized_fixture.html", sanitized)
    _write_json(output_root / "R44I_SELF_TEST_REPORT.json", report)
    return report


def _contract() -> dict[str, Any]:
    return {
        "mode_id": "reddit_logged_in_target_only_visible_session",
        "target_url_rule": "open only the supplied target URL; --direct-launch-target-url starts Chromium with the URL as a browser command-line argument, while --manual-current-page lets the operator manually load it; do not bulk-open branch URLs; after operator pause capture the current visible page without reloading",
        "logged_in_rule": "operator-controlled visible Reddit login/session only; no login automation and no credential entry by the tool",
        "profile_rule": "browser may use an explicitly supplied user-data-dir, but this tool does not inspect, copy, zip, or parse cookies, tokens, Login Data, Local State, Local Storage, cache, or browser profile files",
        "dom_rule": "capture sanitized main Reddit post/comment DOM only; remove right rail, ads, login prompts, cookie banners, scripts and style blocks before R44D",
        "blocker_rule": "if login gate or network security block remains at capture time, stop and write a blocked receipt; initial old-Reddit login redirects are tolerated until the operator finishes the visible redirect/login",
        "downstream_chain": "R44I visible target-only DOM -> R44D -> R43U",
        "remote_media_downloads_enabled": False,
        "cookie_or_token_extraction_enabled": False,
        "login_automation_enabled": False,
        "hidden_platform_api_scraping_enabled": False,
    }



def _find_free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_cdp(port: int, timeout_seconds: int) -> bool:
    deadline = time.time() + max(5, int(timeout_seconds))
    url = f"http://127.0.0.1:{port}/json/version"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def _best_cdp_page(browser: Any, target_url: str) -> Any:
    target_lower = _plain_url(target_url).lower()
    target_path = urlsplit(_plain_url(target_url)).path.lower()
    all_pages: list[Any] = []
    for ctx in browser.contexts:
        all_pages.extend(ctx.pages)
    if not all_pages:
        raise RuntimeError("No pages exposed by Chrome CDP session")
    for pg in reversed(all_pages):
        url = str(getattr(pg, "url", "") or "").lower()
        if target_lower and url == target_lower:
            return pg
    for pg in reversed(all_pages):
        url = str(getattr(pg, "url", "") or "").lower()
        if target_path and target_path in url and "/comments/" in url:
            return pg
    for pg in reversed(all_pages):
        url = str(getattr(pg, "url", "") or "").lower()
        if "reddit.com" in url and "/comments/" in url:
            return pg
    return all_pages[-1]


def _run_live(args: argparse.Namespace, repo: Path, output_root: Path) -> dict[str, Any]:
    target_url = _plain_url(args.target_url)
    capture_ts = _now_ts()
    run_dir = output_root / f"reddit_logged_in_target_only_{capture_ts}"
    evidence_dir = run_dir / "visible_reddit_target_only_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    chromium_executable = args.chromium_executable or _find_default_chromium_executable()
    user_data_dir = args.user_data_dir or _default_user_data_dir()
    if _is_probably_executable_dir(user_data_dir):
        raise SystemExit("Refusing to use chrome-win64/browser executable folder as --user-data-dir. Supply a real profile/user-data folder, or omit --user-data-dir to use the isolated YTCE Reddit profile.")
    if not chromium_executable or not Path(chromium_executable).is_file():
        raise SystemExit(f"Chromium executable not found: {chromium_executable!r}")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise SystemExit(f"Playwright import failed: {exc}")

    request = {
        "marker": MARKER,
        "target_url": target_url,
        "chromium_executable": chromium_executable,
        "user_data_dir": user_data_dir,
        "operator_pause": bool(args.operator_pause),
        "capture_timestamp": capture_ts,
        "navigation_note": "initial navigation errors are tolerated so the operator can finish Reddit login/redirect and capture the currently visible page; --manual-current-page skips Playwright target navigation entirely",
        "manual_current_page": bool(getattr(args, "manual_current_page", False)),
        "direct_launch_target_url": bool(getattr(args, "direct_launch_target_url", False)),
        "remote_debugging_port": int(getattr(args, "remote_debugging_port", 0) or 0),
        "contract": _contract(),
    }
    _write_json(run_dir / "r44i_reddit_logged_in_target_only_request.json", request)

    page_url = ""
    page_text = ""
    sanitized_html = ""
    screenshot_path = evidence_dir / "target_only_current_reddit.png"
    raw_html_path = evidence_dir / "target_only_raw_dom.html"
    sanitized_html_path = evidence_dir / "target_only_sanitized_dom.html"
    initial_navigation_error = ""

    with sync_playwright() as p:
        browser = None
        context = None
        launched_process = None
        if getattr(args, "direct_launch_target_url", False):
            cdp_port = int(args.remote_debugging_port or 0) or _find_free_local_port()
            launch_cmd = [
                chromium_executable,
                f"--user-data-dir={user_data_dir}",
                f"--remote-debugging-port={cdp_port}",
                "--new-window",
                target_url,
            ]
            print("R44I_DIRECT_LAUNCH_TARGET_URL_MODE")
            print("Launching Chromium with the target URL as a browser argument; Playwright will not call page.goto().")
            print("Target URL:")
            print(target_url)
            print("User data dir:")
            print(user_data_dir)
            launched_process = subprocess.Popen(launch_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not _wait_for_cdp(cdp_port, max(10, int(args.timeout_seconds))):
                result = {
                    "marker": MARKER,
                    "status": "BLOCKED_R44I_CDP_NOT_AVAILABLE",
                    "detail": "Chrome did not expose the requested remote debugging port. Close other Chrome-for-Testing windows using the same --user-data-dir, then rerun.",
                    "target_url": target_url,
                    "user_data_dir": user_data_dir,
                    "remote_debugging_port": cdp_port,
                    "side_effect_flags": _side_effect_flags(True, bool(user_data_dir)),
                }
                _write_json(run_dir / "r44i_reddit_logged_in_target_only_receipt.json", result)
                return result
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
            page = _best_cdp_page(browser, target_url)
            initial_navigation_error = "direct_launch_target_url=true; target URL opened by Chromium command line, not by Playwright page.goto"
        else:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                executable_path=chromium_executable,
                headless=False,
                viewport={"width": 1280, "height": 1000},
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = context.pages[0] if context.pages else context.new_page()
        if getattr(args, "manual_current_page", False):
            # Manual mode: do not let Playwright navigate en.reddit.com. Old Reddit
            # can bounce through /login/?reason=lor2 and then eventually load the
            # target in the visible browser; Playwright may treat that as an error.
            # The operator loads the exact target URL manually, then we capture the
            # current page without reloading it.
            initial_navigation_error = "manual_current_page=true; Playwright did not navigate to target URL"
            print("R44I_MANUAL_CURRENT_PAGE_MODE")
            print("Paste/open this exact URL in the visible Chromium window, wait until it is fully loaded, then press Enter in CMD:")
            print(target_url)
            try:
                if not page.url or page.url == "about:blank" or page.url.lower().startswith("chrome://"):
                    page.goto("about:blank", wait_until="load", timeout=5000)
            except Exception:
                pass
        else:
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=max(5000, int(args.timeout_seconds) * 1000))
            except Exception as exc:
                # Old Reddit may first redirect to /login/?reason=lor2 and then, once the
                # operator's signed-in session is recognised, redirect back to the target.
                # Do not abort before the operator can inspect the visible browser.
                initial_navigation_error = str(exc)
                print("R44I_INITIAL_NAVIGATION_WARNING")
                print(initial_navigation_error[:1200])
        page.wait_for_timeout(max(1000, int(args.wait_seconds) * 1000))
        if args.operator_pause or getattr(args, "manual_current_page", False):
            print("\nR44I_OPERATOR_PAUSE")
            print("Use the visible Chromium window to complete Reddit login or verify the target page is loaded.")
            if getattr(args, "direct_launch_target_url", False):
                print("Direct-launch mode: the target URL should already be in the address bar; wait until old Reddit fully renders before pressing Enter.")
            print("The tool will not type credentials, read cookies, or open branch URLs.")
            print("Important: after this pause the tool captures the currently visible page; it will not reload the target URL again.")
            if getattr(args, "manual_current_page", False):
                print("Manual mode: make sure the address bar is the old/en Reddit target URL and the page shows all comments sorted by OLD.")
            input("Press ENTER here when the old/en Reddit target page is visible and ready to capture...")
            page.wait_for_timeout(max(1000, int(args.wait_seconds) * 1000))
        page_url = page.url
        try:
            page_text = page.locator("body").inner_text(timeout=5000)
        except Exception:
            page_text = ""
        blocker, blocker_detail = _blocker_status_from_text(page_url, page_text)
        page.screenshot(path=str(screenshot_path), full_page=True)
        raw_html = page.content()
        _write_text(raw_html_path, raw_html)
        if blocker:
            if context is not None:
                context.close()
            elif browser is not None:
                browser.close()
            result = {
                "marker": MARKER,
                "status": blocker,
                "detail": blocker_detail,
                "target_url": target_url,
                "final_page_url": page_url,
                "initial_navigation_error": initial_navigation_error,
                "screenshot_path": str(screenshot_path),
                "raw_html_path": str(raw_html_path),
                "side_effect_flags": _side_effect_flags(True, bool(user_data_dir)),
            }
            _write_json(run_dir / "r44i_reddit_logged_in_target_only_receipt.json", result)
            return result
        # Sanitise from captured page.content() in Python instead of browser-side JS.
        # The earlier browser-side page.evaluate sanitizer could fail with a JS
        # SyntaxError when escape sequences were interpreted inside the injected
        # expression. Python-side sanitising is enough for old Reddit and keeps
        # manual-current-page capture from reloading or touching the live page.
        sanitized_html = _sanitize_current_reddit_dom_html(raw_html)
        if context is not None:
            context.close()
        elif browser is not None:
            browser.close()

    if not _sanitized_html_has_target_content(sanitized_html):
        sanitized_html = raw_html
    sanitized_html = _sanitize_current_reddit_dom_html(sanitized_html or raw_html)
    if not _sanitized_html_has_target_content(sanitized_html):
        sanitized_html = _sanitize_current_reddit_dom_html(raw_html)
    _write_text(sanitized_html_path, sanitized_html)

    sys.path.insert(0, str(repo))
    from profile_media_reddit_visible_dom_capture_r44d import (  # type: ignore
        RedditVisibleDomCaptureRequestR44D,
        run_reddit_visible_dom_capture_r44d,
    )

    r44d_output = run_dir / "r44d_target_only_capture"
    r44d_result = run_reddit_visible_dom_capture_r44d(
        RedditVisibleDomCaptureRequestR44D(
            account_url=target_url,
            account_handle=args.account_handle,
            capture_timestamp=capture_ts,
            output_root=str(r44d_output),
            visible_dom_html_path=str(sanitized_html_path),
            static_screenshot_path=str(screenshot_path),
            feed_mode="single_thread",
            include_comments=True,
            include_media=True,
            include_static_screenshots=True,
            require_screenshot_receipts=True,
            max_items=max(1, int(args.max_items)),
        )
    )
    payload = r44d_result.to_dict()
    status = PASS_STATUS if payload.get("status") == "PASS_R44D_REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER" else BLOCKED_STATUS
    result = {
        "marker": MARKER,
        "status": status,
        "target_url": target_url,
        "final_page_url": page_url,
        "initial_navigation_error": initial_navigation_error,
        "manual_current_page": bool(getattr(args, "manual_current_page", False)),
        "direct_launch_target_url": bool(getattr(args, "direct_launch_target_url", False)),
        "remote_debugging_port": int(getattr(args, "remote_debugging_port", 0) or 0),
        "capture_timestamp": capture_ts,
        "run_dir": str(run_dir),
        "raw_html_path": str(raw_html_path),
        "sanitized_html_path": str(sanitized_html_path),
        "screenshot_path": str(screenshot_path),
        "r44d_status": payload.get("status"),
        "ledger_status": payload.get("ledger_status"),
        "record_count": payload.get("record_count"),
        "media_count": payload.get("media_count"),
        "screenshot_count": payload.get("screenshot_count"),
        "visible_record_count": payload.get("visible_record_count"),
        "warnings": payload.get("warnings") or [],
        "side_effect_flags": _side_effect_flags(True, bool(user_data_dir)),
        "r44d_receipt_path": payload.get("receipt_path"),
    }
    _write_json(run_dir / "r44i_reddit_logged_in_target_only_receipt.json", result)
    return result


def _side_effect_flags(browser_started: bool, profile_used: bool) -> dict[str, bool]:
    return {
        "browser_session_started": bool(browser_started),
        "operator_controlled_browser_profile_used_by_browser_process": bool(profile_used),
        "target_url_only_no_branch_loop": True,
        "browser_profile_files_copied_by_tool": False,
        "browser_profile_files_parsed_by_tool": False,
        "cookie_or_token_extraction_performed": False,
        "login_automation_performed": False,
        "captcha_or_challenge_bypass_performed": False,
        "hidden_platform_api_scraping_performed": False,
        "remote_media_downloads_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="R44I Reddit logged-in target-only visible session smoke")
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL)
    parser.add_argument("--account-handle", default=DEFAULT_ACCOUNT_HANDLE)
    parser.add_argument("--output-root", default="profile_media_live_captures/r44i_reddit_logged_in_target_only_visible_session")
    parser.add_argument("--chromium-executable", default="")
    parser.add_argument("--user-data-dir", default="")
    parser.add_argument("--wait-seconds", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--max-items", type=int, default=500)
    parser.add_argument("--operator-pause", action="store_true")
    parser.add_argument("--manual-current-page", action="store_true", help="Do not navigate with Playwright; operator manually loads target URL, then capture the current visible page without reloading.")
    parser.add_argument("--direct-launch-target-url", action="store_true", help="Launch Chromium with the target URL on the command line, connect by CDP, then capture the current page without using page.goto().")
    parser.add_argument("--remote-debugging-port", type=int, default=0, help="Optional CDP port for --direct-launch-target-url. Default: choose a free local port.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    repo = Path.cwd()
    output_root = Path(args.output_root)
    if args.self_test:
        report = _run_self_test(output_root / "self_test")
        print(MARKER)
        print(report["status"])
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == PASS_STATUS else 1

    result = _run_live(args, repo, output_root)
    print(MARKER)
    print(result.get("status"))
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("status") == PASS_STATUS:
        print("R44I_REDDIT_LOGGED_IN_TARGET_ONLY_VISIBLE_SESSION_DONE")
        return 0
    print("R44I_REDDIT_LOGGED_IN_TARGET_ONLY_VISIBLE_SESSION_BLOCKED")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


def build_reddit_logged_in_target_only_visible_session_contract_r44i() -> dict[str, Any]:
    """Return the R44I safety/route contract for app registration and tests."""
    return _contract()
