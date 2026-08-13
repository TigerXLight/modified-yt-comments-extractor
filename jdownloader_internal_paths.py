from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping


JDOWNLOADER_INTERNAL_BACKEND_ID = "jdownloader_internal"
YTDLP_FALLBACK_BACKEND_ID = "yt_dlp_fallback"

REPO_ROOT = Path(__file__).resolve().parent
JD_VENDOR_ROOT = REPO_ROOT / "third_party" / "jdownloader"
JD_SOURCE_ARCHIVES_DIR = JD_VENDOR_ROOT / "source_archives"
JD_SOURCE_TREE_DIR = JD_VENDOR_ROOT / "source_tree"
JD_RUNTIME_DIR = JD_VENDOR_ROOT / "runtime" / "JDownloader 2"
JD_MANIFESTS_DIR = JD_VENDOR_ROOT / "manifests"
JD_BRIDGE_SRC_DIR = JD_VENDOR_ROOT / "bridge" / "src"
JD_BRIDGE_BUILD_DIR = JD_VENDOR_ROOT / "bridge" / "build"

LOCAL_JD_MIRROR_ROOT = Path(r"C:\Users\fahad\Downloads\jdownloader_mirror-main\jdownloader_mirror-main")
LOCAL_JD_INSTALLED_ROOT = Path(r"C:\Users\fahad\AppData\Local\JDownloader 2")
LOCAL_BUNDLE_ZIP = Path(r"C:\Users\fahad\Downloads\YTCE_CODEX_JDOWNLOADER_INTERNAL_ENGINE_AND_TWITTER_V27_BUNDLE_20260813.zip")
LOCAL_BUNDLE_INPUT_PREFIX = "ytce_codex_jdownloader_internal_engine_and_twitter_v27_bundle_20260813/inputs/"

JD_SOURCE_ARCHIVE_SOURCES: Mapping[str, Path] = {
    "svn_browser.zip": LOCAL_JD_MIRROR_ROOT / "svn_browser" / "svn_browser.zip",
    "svn_MyJDownloaderClient.zip": LOCAL_JD_MIRROR_ROOT / "svn_MyJDownloaderClient" / "svn_MyJDownloaderClient.zip",
    "svn_utils.zip": LOCAL_JD_MIRROR_ROOT / "svn_utils" / "svn_utils.zip",
    "src.zip": LOCAL_JD_MIRROR_ROOT / "svn_trunk" / "src" / "src.zip",
    "JDownloader_Dev_Libs_Backup.zip": LOCAL_JD_MIRROR_ROOT / "JDownloader_Dev_Libs_Backup.zip",
    "JDownloader.jar": LOCAL_JD_MIRROR_ROOT / "svn_trunk" / "dev" / "JDownloader.jar",
    "CLAUDE.md": LOCAL_JD_MIRROR_ROOT / "svn_trunk" / "CLAUDE.md",
    "captchaMethodChecker.java": LOCAL_JD_MIRROR_ROOT / "svn_trunk" / "tools" / "captchaMethodChecker.java",
    "cobra_ext.jar": LOCAL_JD_MIRROR_ROOT / "svn_trunk" / "tools" / "cobra_ext.jar",
    "complete_mirror_addresses.txt": LOCAL_JD_MIRROR_ROOT / "complete_mirror_addresses.txt",
    "complete_jdownloader_files.txt": LOCAL_JD_INSTALLED_ROOT / "complete_jdownloader_files.txt",
}

JD_RUNTIME_SOURCE_FILES: Mapping[str, Path] = {
    "JDownloader 2.zip": LOCAL_JD_INSTALLED_ROOT / "JDownloader 2.zip",
    "JDownloader.jar": LOCAL_JD_INSTALLED_ROOT / "JDownloader.jar",
    "JDownloader2.exe": LOCAL_JD_INSTALLED_ROOT / "JDownloader2.exe",
    "Core.jar": LOCAL_JD_INSTALLED_ROOT / "Core.jar",
    "cfg/org.jdownloader.api.RemoteAPIConfig.json": LOCAL_JD_INSTALLED_ROOT / "cfg" / "org.jdownloader.api.RemoteAPIConfig.json",
    "cfg/plugins/youtube/Youtube.json": LOCAL_JD_INSTALLED_ROOT / "cfg" / "plugins" / "youtube" / "Youtube.json",
    "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.json": LOCAL_JD_INSTALLED_ROOT / "cfg" / "org.jdownloader.controlling.ffmpeg.FFmpegSetup.json",
    "tools/Windows/ffmpeg/x64/ffmpeg.exe": LOCAL_JD_INSTALLED_ROOT / "tools" / "Windows" / "ffmpeg" / "x64" / "ffmpeg.exe",
    "tools/Windows/ffmpeg/x64/ffprobe.exe": LOCAL_JD_INSTALLED_ROOT / "tools" / "Windows" / "ffmpeg" / "x64" / "ffprobe.exe",
}

JD_REQUIRED_YOUTUBE_SOURCE_PATHS = (
    "jd/plugins/hoster/YoutubeDashV2.java",
    "org/jdownloader/plugins/components/youtube/YoutubeHelper.java",
    "org/jdownloader/plugins/components/youtube/YoutubeClipData.java",
    "org/jdownloader/plugins/components/youtube/ClipDataCache.java",
    "org/jdownloader/plugins/components/youtube/StreamCollection.java",
    "org/jdownloader/plugins/components/youtube/YoutubeStreamData.java",
    "org/jdownloader/plugins/components/youtube/YoutubeFinalLinkResource.java",
    "org/jdownloader/plugins/components/youtube/YoutubeReplacer.java",
    "org/jdownloader/plugins/components/youtube/itag/YoutubeITAG.java",
    "org/jdownloader/plugins/components/youtube/itag/VideoCodec.java",
    "org/jdownloader/plugins/components/youtube/itag/AudioCodec.java",
    "org/jdownloader/plugins/components/youtube/itag/VideoResolution.java",
    "org/jdownloader/plugins/components/youtube/variants/VideoVariant.java",
    "org/jdownloader/plugins/components/youtube/variants/AudioVariant.java",
    "org/jdownloader/plugins/components/youtube/variants/SubtitleVariant.java",
    "org/jdownloader/plugins/components/youtube/variants/ImageVariant.java",
    "org/jdownloader/plugins/components/youtube/variants/VariantGroup.java",
    "org/jdownloader/plugins/components/youtube/variants/VariantBase.java",
    "org/jdownloader/plugins/components/youtube/converter/YoutubeConverter.java",
    "org/jdownloader/plugins/components/youtube/converter/YoutubeConverterMP4ToM4AAudio.java",
    "org/jdownloader/plugins/components/youtube/YoutubeConfig.java",
    "org/jdownloader/settings/staticreferences/CFG_YOUTUBE.java",
)

JD_REQUIRED_CONTROL_SOURCE_PATHS = (
    "org/jdownloader/api/cnl2/ExternInterface.java",
    "org/jdownloader/api/cnl2/ExternInterfaceImpl.java",
    "org/jdownloader/api/cnl2/Cnl2APIFlash.java",
    "org/jdownloader/api/cnl2/CnlQueryStorable.java",
    "org/jdownloader/api/accounts/v2/",
    "org/jdownloader/api/captcha/",
    "org/jdownloader/myjdownloader/client/bindings/AddLinksQuery.java",
    "org/jdownloader/myjdownloader/client/bindings/linkgrabberv2/",
)


@dataclass(frozen=True)
class JDownloaderInternalLayout:
    repo_root: str
    vendor_root: str
    source_archives_dir: str
    source_tree_dir: str
    runtime_dir: str
    manifests_dir: str
    bridge_src_dir: str
    bridge_build_dir: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def internal_jdownloader_layout(repo_root: str | Path | None = None) -> JDownloaderInternalLayout:
    root = Path(repo_root).resolve() if repo_root is not None else REPO_ROOT
    vendor = root / "third_party" / "jdownloader"
    return JDownloaderInternalLayout(
        repo_root=str(root),
        vendor_root=str(vendor),
        source_archives_dir=str(vendor / "source_archives"),
        source_tree_dir=str(vendor / "source_tree"),
        runtime_dir=str(vendor / "runtime" / "JDownloader 2"),
        manifests_dir=str(vendor / "manifests"),
        bridge_src_dir=str(vendor / "bridge" / "src"),
        bridge_build_dir=str(vendor / "bridge" / "build"),
    )
