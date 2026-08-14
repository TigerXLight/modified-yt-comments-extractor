from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


HOSTER_DIR_PARTS = ("jd", "plugins", "hoster")
DECRYPTER_DIR_PARTS = ("jd", "plugins", "decrypter")
DEFAULT_RUNTIME_ROOT = Path("third_party") / "jdownloader" / "runtime" / "JDownloader 2"
DEFAULT_OUTPUT_PATH = Path("jd_capabilities_manifest.json")


@dataclass(frozen=True)
class JDownloaderPluginRecord:
    plugin_type: str
    plugin_name: str
    relative_path: str
    domains: tuple[str, ...] = ()
    source_kind: str = "runtime"


@dataclass
class JDownloaderDomainCapability:
    media_backend: str = "jdownloader"
    tested: bool = False
    supports_video: Any = "unknown_until_tested"
    supports_audio: Any = "unknown_until_tested"
    supports_thumbnail: Any = "unknown_until_tested"
    supports_description: Any = "unknown_until_tested"
    supports_subtitles: Any = "unknown_until_tested"
    plugin_types: set[str] = field(default_factory=set)
    plugins: list[dict[str, str]] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        return {
            "media_backend": self.media_backend,
            "tested": self.tested,
            "supports_video": self.supports_video,
            "supports_audio": self.supports_audio,
            "supports_thumbnail": self.supports_thumbnail,
            "supports_description": self.supports_description,
            "supports_subtitles": self.supports_subtitles,
            "plugin_types": sorted(self.plugin_types),
            "plugins": sorted(self.plugins, key=lambda item: (item["plugin_type"], item["plugin_name"], item["relative_path"])),
        }


def _normalise_domain(value: str) -> str:
    value = value.strip().strip('"').strip("'").lower()
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^www\.", "", value)
    value = value.split("/", 1)[0]
    value = value.split(":", 1)[0]
    return value.strip()


def _camel_plugin_name_to_domain(plugin_name: str) -> str | None:
    # Basic fallback for runtime .class files when Java annotations are unavailable.
    stem = Path(plugin_name).stem
    if not stem or len(stem) < 4:
        return None

    lowered = stem.lower()
    manual = {
        "youtubecom": "youtube.com",
        "twittercom": "twitter.com",
        "xcom": "x.com",
        "instagramcom": "instagram.com",
        "tiktokcom": "tiktok.com",
        "redditcom": "reddit.com",
        "facebookcom": "facebook.com",
        "vimeocom": "vimeo.com",
        "dailymotioncom": "dailymotion.com",
        "soundcloudcom": "soundcloud.com",
    }
    if lowered in manual:
        return manual[lowered]

    tlds = ("com", "org", "net", "co", "io", "tv", "de", "uk", "info", "ru", "jp", "to", "me")
    for tld in tlds:
        if lowered.endswith(tld) and len(lowered) > len(tld) + 2:
            host = lowered[: -len(tld)]
            if host:
                return f"{host}.{tld}"
    return None


def _extract_domains_from_java(text: str) -> tuple[str, ...]:
    domains: set[str] = set()

    # JDownloader plugin annotations commonly use:
    # @HostPlugin(names = { "youtube.com" }, urls = { ... })
    # @DecrypterPlugin(names = { "twitter.com" }, urls = { ... })
    for match in re.finditer(r"names\s*=\s*\{(?P<body>[^}]+)\}", text, flags=re.I | re.S):
        body = match.group("body")
        for raw in re.findall(r'"([^"]+)"', body):
            domain = _normalise_domain(raw)
            if "." in domain and not any(ch in domain for ch in "*()[]{}|\\"):
                domains.add(domain)

    # Some plugin source contains getAnnotationNames()/site arrays, so use a
    # conservative domain regex as a fallback, while avoiding generic file names.
    for raw in re.findall(r'\b(?:[a-z0-9-]+\.)+(?:com|org|net|co|io|tv|de|uk|info|ru|jp|to|me)\b', text, flags=re.I):
        domain = _normalise_domain(raw)
        if domain and not domain.endswith(".java"):
            domains.add(domain)

    return tuple(sorted(domains))


def _plugin_type_from_path(path: Path) -> str | None:
    lowered = tuple(part.lower() for part in path.parts)
    hoster = tuple(part.lower() for part in HOSTER_DIR_PARTS)
    decrypter = tuple(part.lower() for part in DECRYPTER_DIR_PARTS)
    for idx in range(0, len(lowered) - len(hoster) + 1):
        if lowered[idx : idx + len(hoster)] == hoster:
            return "hoster"
    for idx in range(0, len(lowered) - len(decrypter) + 1):
        if lowered[idx : idx + len(decrypter)] == decrypter:
            return "decrypter"
    return None


def _iter_candidate_plugin_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    return (
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".java", ".class"}
        and _plugin_type_from_path(path) in {"hoster", "decrypter"}
    )


def scan_jdownloader_plugins(runtime_root: str | Path, source_root: str | Path | None = None) -> tuple[JDownloaderPluginRecord, ...]:
    roots: list[tuple[Path, str]] = [(Path(runtime_root), "runtime")]
    if source_root:
        roots.append((Path(source_root), "source"))

    records: list[JDownloaderPluginRecord] = []
    seen: set[tuple[str, str, str, tuple[str, ...]]] = set()

    for root, source_kind in roots:
        if not root.exists():
            continue
        for path in _iter_candidate_plugin_files(root):
            plugin_type = _plugin_type_from_path(path)
            if plugin_type is None:
                continue
            rel = str(path.relative_to(root)).replace("\\", "/")
            domains: tuple[str, ...] = ()
            if path.suffix.lower() == ".java":
                try:
                    domains = _extract_domains_from_java(path.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    domains = ()
            if not domains:
                inferred = _camel_plugin_name_to_domain(path.stem)
                domains = (inferred,) if inferred else ()
            key = (plugin_type, path.stem, rel, domains)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                JDownloaderPluginRecord(
                    plugin_type=plugin_type,
                    plugin_name=path.stem,
                    relative_path=rel,
                    domains=tuple(sorted(set(domains))),
                    source_kind=source_kind,
                )
            )

    return tuple(sorted(records, key=lambda item: (item.plugin_type, item.plugin_name, item.relative_path)))


def _apply_known_ytce_overrides(capabilities: dict[str, JDownloaderDomainCapability]) -> None:
    for domain in ("youtube.com", "youtu.be"):
        cap = capabilities.setdefault(domain, JDownloaderDomainCapability())
        cap.tested = True
        cap.supports_video = True
        cap.supports_audio = True
        cap.supports_thumbnail = True
        cap.supports_description = True
        cap.supports_subtitles = "depends_on_source_video"


def build_jdownloader_capabilities_manifest(
    runtime_root: str | Path = DEFAULT_RUNTIME_ROOT,
    source_root: str | Path | None = None,
    *,
    apply_ytce_overrides: bool = True,
) -> dict[str, Any]:
    runtime_root = Path(runtime_root)
    source_root_path = Path(source_root) if source_root else None
    records = scan_jdownloader_plugins(runtime_root, source_root_path)

    capabilities: dict[str, JDownloaderDomainCapability] = {}
    unknown_domain_plugins: list[dict[str, str]] = []

    for record in records:
        plugin_json = {
            "plugin_type": record.plugin_type,
            "plugin_name": record.plugin_name,
            "relative_path": record.relative_path,
            "source_kind": record.source_kind,
        }
        if not record.domains:
            unknown_domain_plugins.append(plugin_json)
            continue
        for domain in record.domains:
            cap = capabilities.setdefault(domain, JDownloaderDomainCapability())
            cap.plugin_types.add(record.plugin_type)
            cap.plugins.append(plugin_json)

    if apply_ytce_overrides:
        _apply_known_ytce_overrides(capabilities)

    manifest = {
        "schema_version": 1,
        "generated_at_unix": int(time.time()),
        "generated_by": "tools/generate_jdownloader_capabilities_manifest_v66.py",
        "runtime_root": str(runtime_root),
        "source_root": str(source_root_path) if source_root_path else None,
        "dev_only": True,
        "startup_safe": "not_loaded_on_app_startup",
        "notes": [
            "This manifest is generated by a manual developer tool.",
            "It is a capability index for routing/backend planning, not copied JD implementation code.",
            "Credentials and JDownloader account data are not read.",
            "Unknown support values must be verified by real download tests before being advertised in the UI.",
        ],
        "counts": {
            "plugin_files_scanned": len(records),
            "domains": len(capabilities),
            "unknown_domain_plugins": len(unknown_domain_plugins),
            "hoster_plugins": sum(1 for record in records if record.plugin_type == "hoster"),
            "decrypter_plugins": sum(1 for record in records if record.plugin_type == "decrypter"),
        },
        "capabilities": {domain: capabilities[domain].as_json() for domain in sorted(capabilities)},
        "unknown_domain_plugins": sorted(unknown_domain_plugins, key=lambda item: (item["plugin_type"], item["plugin_name"], item["relative_path"])),
    }
    return manifest


def write_jdownloader_capabilities_manifest(
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    runtime_root: str | Path = DEFAULT_RUNTIME_ROOT,
    source_root: str | Path | None = None,
    *,
    apply_ytce_overrides: bool = True,
) -> Path:
    manifest = build_jdownloader_capabilities_manifest(
        runtime_root=runtime_root,
        source_root=source_root,
        apply_ytce_overrides=apply_ytce_overrides,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a dev-only JDownloader capability manifest.")
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT), help="Project-local JDownloader runtime root.")
    parser.add_argument("--source-root", default=None, help="Optional unpacked JD source/mirror root for Java annotation scanning.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output manifest path.")
    parser.add_argument("--no-ytce-overrides", action="store_true", help="Do not mark YTCE-proven YouTube capabilities.")
    args = parser.parse_args(argv)

    output = write_jdownloader_capabilities_manifest(
        output_path=args.output,
        runtime_root=args.runtime_root,
        source_root=args.source_root,
        apply_ytce_overrides=not args.no_ytce_overrides,
    )
    manifest = json.loads(output.read_text(encoding="utf-8"))
    print(f"WROTE {output}")
    print(f"DOMAINS {manifest['counts']['domains']}")
    print(f"PLUGIN_FILES_SCANNED {manifest['counts']['plugin_files_scanned']}")
    print("DEV_ONLY true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
