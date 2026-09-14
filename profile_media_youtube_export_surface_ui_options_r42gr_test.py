from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

from main import App
from profile_media_youtube_export_surface_ui_options_r42gr import (
    R42GR_MARKER,
    R42GR_PASS_STATUS,
    YouTubeExportSurfaceOptions,
    build_youtube_export_surface_options,
    collect_youtube_export_surface_options_from_vars,
    generate_ui_options_report,
)


def _assert(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(str(message))


class _Var:
    def __init__(self, value: bool) -> None:
        self.value = value

    def get(self) -> bool:
        return self.value


def test_options_model_defaults_both_choices_off() -> None:
    options = build_youtube_export_surface_options()
    _assert(options == YouTubeExportSurfaceOptions(), options)
    _assert(options.to_settings_dict() == {
        "include_youtube_searchable_html": False,
        "include_author_profile_urls": False,
    }, options.to_settings_dict())
    _assert(options.to_create_evidence_package_kwargs() == {
        "include_youtube_searchable_html": False,
        "include_author_profile_urls": False,
    }, options.to_create_evidence_package_kwargs())


def test_var_collection_passes_enabled_booleans_to_export_kwargs() -> None:
    options = collect_youtube_export_surface_options_from_vars(_Var(True), _Var(True))
    kwargs = options.to_create_evidence_package_kwargs()
    _assert(kwargs["include_youtube_searchable_html"] is True, kwargs)
    _assert(kwargs["include_author_profile_urls"] is True, kwargs)


def test_report_generates_options_off_and_on_outputs_without_side_effects() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = generate_ui_options_report(".", Path(tmp) / "r42gr")
        report_path = Path(tmp) / "r42gr" / "R42GR_YOUTUBE_EXPORT_SURFACE_UI_OPTIONS_REPORT.json"
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        off_dir = Path(payload["options_off_package"]["output_dir"])
        on_dir = Path(payload["options_on_package"]["output_dir"])
        on_html = on_dir / "youtube-comments-searchable.html"
        source_info = (on_dir / "source_info.txt").read_text(encoding="utf-8")

        _assert(report.marker == R42GR_MARKER, report.to_dict())
        _assert(report.status == R42GR_PASS_STATUS, report.to_dict())
        _assert(payload["default_options"]["include_youtube_searchable_html"] is False, payload)
        _assert(payload["default_options"]["include_author_profile_urls"] is False, payload)
        _assert((off_dir / "comments_readable.txt").exists(), str(off_dir))
        _assert("searchable_html_path" not in payload["options_off_package"], payload["options_off_package"])
        _assert(not (off_dir / "youtube-comments-searchable.html").exists(), str(off_dir))
        _assert(not (off_dir / "youtube-author-profile-sidecar.json").exists(), str(off_dir))
        _assert(not (off_dir / "youtube-author-profile-sidecar.csv").exists(), str(off_dir))
        _assert(not (off_dir / "youtube-author-profile-sidecar.html").exists(), str(off_dir))
        _assert((on_dir / "comments_readable.txt").exists(), str(on_dir))
        _assert(on_html.exists(), str(on_html))
        _assert((on_dir / "youtube-author-profile-sidecar.json").exists(), str(on_dir))
        _assert((on_dir / "screenshots").exists(), str(on_dir))
        _assert("YouTube Comments - Readable Evidence Export" in (on_dir / "comments_readable.txt").read_text(encoding="utf-8"), "readable txt changed")
        _assert("id=\"searchBox\"" in on_html.read_text(encoding="utf-8"), on_html)
        _assert("http://" not in on_html.read_text(encoding="utf-8").lower().split("<script", 1)[0], "remote script/style guard")
        _assert("include_youtube_searchable_html" in source_info, source_info)
        _assert("include_author_profile_urls" in source_info, source_info)
        encoded = json.dumps(payload)
        _assert("](" not in encoded and r"]\(" not in encoded, encoded)
        _assert(payload["status"] == R42GR_PASS_STATUS, payload)


def test_main_ui_exposes_youtube_export_options_and_export_passes_booleans() -> None:
    window_source = inspect.getsource(App._open_youtube_filter_settings_window)
    export_source = inspect.getsource(App.export_evidence_folder)
    init_source = inspect.getsource(App.__init__)

    _assert("Create searchable comments HTML" in window_source, window_source)
    _assert("Include author channel/profile URL sidecars" in window_source, window_source)
    _assert("youtube_export_searchable_html_var = ctk.BooleanVar(value=False)" in init_source, init_source)
    _assert("youtube_export_author_profile_urls_var = ctk.BooleanVar(value=False)" in init_source, init_source)
    _assert("collect_youtube_export_surface_options_from_vars" in export_source, export_source)
    _assert("to_settings_dict()" in export_source, export_source)
    _assert("to_create_evidence_package_kwargs()" in export_source, export_source)


def run_all_tests() -> None:
    test_options_model_defaults_both_choices_off()
    test_var_collection_passes_enabled_booleans_to_export_kwargs()
    test_report_generates_options_off_and_on_outputs_without_side_effects()
    test_main_ui_exposes_youtube_export_options_and_export_passes_booleans()


if __name__ == "__main__":
    run_all_tests()
    print("profile_media_youtube_export_surface_ui_options_r42gr_test: PASS")
