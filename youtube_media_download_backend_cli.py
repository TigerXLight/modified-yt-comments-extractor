from __future__ import annotations

import argparse
import json
from pathlib import Path

from media_jdownloader_external_config import load_jdownloader_external_config, resolve_jdownloader_source_path, write_jdownloader_external_config_report
from youtube_media_download_backend import (
    build_youtube_ytdlp_download_plan,
    normalize_media_source_url_arg_strict,
    resolve_ytdlp_command,
    discover_youtube_media_with_ytdlp,
    run_youtube_ytdlp_download_plan,
    write_youtube_media_download_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="YouTube media discovery/download backend using yt-dlp + FFmpeg.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--yt-dlp", default="auto")
    parser.add_argument("--ffmpeg-location", default="")
    parser.add_argument("--jdownloader-root-or-zip", default="")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-auto-subs", action="store_true")
    args = parser.parse_args()

    source_url = normalize_media_source_url_arg_strict(args.source_url)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        ytdlp_resolution = resolve_ytdlp_command(args.yt_dlp, repo_root=Path(__file__).resolve().parent)
    except FileNotFoundError as exc:
        message = str(exc)
        (out / "youtube-media-download-tool-error.txt").write_text(message + "\n", encoding="utf-8")
        print("YOUTUBE_MEDIA_YTDLP_NOT_FOUND=" + message)
        print("YOUTUBE_MEDIA_INSTALL_YTDLP=venv\\Scripts\\python.exe -m pip install -U yt-dlp")
        return 2

    yt_dlp_command = ytdlp_resolution.command
    print("YOUTUBE_MEDIA_YTDLP_SOURCE=" + ytdlp_resolution.source)
    print("YOUTUBE_MEDIA_YTDLP_COMMAND=" + " ".join(yt_dlp_command))

    jd_config = None
    if args.jdownloader_root_or_zip:
        jd_source = resolve_jdownloader_source_path(args.jdownloader_root_or_zip)
        print("JDOWNLOADER_SOURCE=" + str(jd_source))
        jd_config = load_jdownloader_external_config(jd_source)
        write_jdownloader_external_config_report(jd_source, out / "jdownloader-external-config-report.json")

    discovery = None
    if args.discover:
        discovery = discover_youtube_media_with_ytdlp(
            source_url,
            yt_dlp_path=yt_dlp_command,
            output_dir=out,
        )
        (out / "youtube-media-discovery.json").write_text(
            json.dumps(discovery.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    plan = build_youtube_ytdlp_download_plan(
        source_url,
        output_dir=out,
        yt_dlp_path=yt_dlp_command,
        ffmpeg_location=args.ffmpeg_location,
        jdownloader_config=jd_config,
        write_auto_subtitles=args.write_auto_subs,
        dry_run=not args.execute,
    )
    write_youtube_media_download_plan(plan, out / "youtube-media-download-plan.json")
    print("YOUTUBE_MEDIA_BACKEND_MODULE=" + __import__("youtube_media_download_backend").__file__)
    print("YOUTUBE_MEDIA_DOWNLOAD_PLAN=" + str(out / "youtube-media-download-plan.json"))
    print("YOUTUBE_MEDIA_SOURCE_URL=" + source_url)
    print("YOUTUBE_MEDIA_FORMAT_SELECTOR=" + plan.format_selector)
    print("YOUTUBE_MEDIA_DRY_RUN=" + str(plan.dry_run))
    if discovery is not None:
        print("YOUTUBE_MEDIA_DISCOVERED_FORMATS=" + str(len(discovery.formats)))
    if args.execute:
        completed = run_youtube_ytdlp_download_plan(plan)
        (out / "youtube-media-download-stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
        (out / "youtube-media-download-stderr.txt").write_text(completed.stderr or "", encoding="utf-8")
        print("YOUTUBE_MEDIA_DOWNLOAD_RETURNCODE=" + str(completed.returncode))
        return int(completed.returncode or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
