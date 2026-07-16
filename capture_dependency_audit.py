from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEPENDENCY_DECISION_SELECT = "SELECT"
DEPENDENCY_DECISION_SELECT_WITH_NOTICE = "SELECT_WITH_NOTICE"
DEPENDENCY_DECISION_SELECT_OPTIONAL = "SELECT_OPTIONAL"
DEPENDENCY_DECISION_OPTIONAL_EXTERNAL = "OPTIONAL_EXTERNAL"
DEPENDENCY_DECISION_OPTIONAL_EXTERNAL_OR_PYTHON = "OPTIONAL_EXTERNAL_OR_PYTHON"
DEPENDENCY_DECISION_USER_CONFIGURED_EXTERNAL = "USER_CONFIGURED_EXTERNAL"
DEPENDENCY_DECISION_EXTERNAL_ONLY = "EXTERNAL_ONLY"
DEPENDENCY_DECISION_REVIEW = "REVIEW"
DEPENDENCY_DECISION_REFERENCE = "REFERENCE"

DEPENDENCY_SCOPE_OPTIONAL_PYTHON = "optional_python_dependency"
DEPENDENCY_SCOPE_OPTIONAL_TEST = "optional_test_dependency"
DEPENDENCY_SCOPE_EXTERNAL_TOOL = "external_tool"
DEPENDENCY_SCOPE_REFERENCE_ONLY = "reference_only"

DEPENDENCY_AUDIT_SCOPE = (
    "dependency and licence audit metadata only; no install, import, browser download, "
    "external process execution, network call, archive action, media download, or GUI behavior"
)


@dataclass(frozen=True)
class CaptureDependencyAuditItem:
    name: str
    license: str
    role: str
    decision: str
    scope: str
    optional: bool = True
    auto_install: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "auto_install": self.auto_install,
            "decision": self.decision,
            "license": self.license,
            "name": self.name,
            "notes": self.notes,
            "optional": self.optional,
            "role": self.role,
            "scope": self.scope,
        }


CAPTURE_DEPENDENCY_AUDIT_ITEMS: tuple[CaptureDependencyAuditItem, ...] = (
    CaptureDependencyAuditItem(
        name="playwright",
        license="Apache-2.0",
        role="browser capture",
        decision=DEPENDENCY_DECISION_SELECT,
        scope=DEPENDENCY_SCOPE_OPTIONAL_PYTHON,
        notes="Primary optional browser runtime; install and browser download are separate explicit steps.",
    ),
    CaptureDependencyAuditItem(
        name="Mozilla Readability",
        license="Apache-2.0",
        role="article candidate",
        decision=DEPENDENCY_DECISION_SELECT_WITH_NOTICE,
        scope=DEPENDENCY_SCOPE_OPTIONAL_PYTHON,
        notes="Pin exact reviewed package/build and preserve notices before runtime use.",
    ),
    CaptureDependencyAuditItem(
        name="trafilatura",
        license="Apache-2.0",
        role="article extraction",
        decision=DEPENDENCY_DECISION_SELECT,
        scope=DEPENDENCY_SCOPE_OPTIONAL_PYTHON,
        notes="Optional consensus/alternative extractor.",
    ),
    CaptureDependencyAuditItem(
        name="httpx",
        license="BSD-3-Clause",
        role="HTTP providers/downloads",
        decision=DEPENDENCY_DECISION_SELECT,
        scope=DEPENDENCY_SCOPE_OPTIONAL_PYTHON,
    ),
    CaptureDependencyAuditItem(
        name="jsonschema",
        license="MIT",
        role="contract validation",
        decision=DEPENDENCY_DECISION_SELECT,
        scope=DEPENDENCY_SCOPE_OPTIONAL_PYTHON,
    ),
    CaptureDependencyAuditItem(
        name="warcio",
        license="Apache-2.0",
        role="WARC",
        decision=DEPENDENCY_DECISION_SELECT_OPTIONAL,
        scope=DEPENDENCY_SCOPE_OPTIONAL_PYTHON,
    ),
    CaptureDependencyAuditItem(
        name="py-wacz",
        license="Apache-2.0",
        role="WACZ",
        decision=DEPENDENCY_DECISION_SELECT_OPTIONAL,
        scope=DEPENDENCY_SCOPE_OPTIONAL_PYTHON,
    ),
    CaptureDependencyAuditItem(
        name="aiohttp",
        license="Apache-2.0/MIT",
        role="fixture HTTP server",
        decision=DEPENDENCY_DECISION_SELECT_OPTIONAL,
        scope=DEPENDENCY_SCOPE_OPTIONAL_TEST,
    ),
    CaptureDependencyAuditItem(
        name="websockets",
        license="BSD-3-Clause",
        role="livechat fixture",
        decision=DEPENDENCY_DECISION_SELECT_OPTIONAL,
        scope=DEPENDENCY_SCOPE_OPTIONAL_TEST,
    ),
    CaptureDependencyAuditItem(
        name="ffmpeg",
        license="LGPL/GPL build-dependent",
        role="mux/transcode",
        decision=DEPENDENCY_DECISION_USER_CONFIGURED_EXTERNAL,
        scope=DEPENDENCY_SCOPE_EXTERNAL_TOOL,
        auto_install=False,
        notes="No silent system installation; record actual build and licence.",
    ),
    CaptureDependencyAuditItem(
        name="yt-dlp",
        license="Unlicense core; binary contents vary",
        role="media backend",
        decision=DEPENDENCY_DECISION_OPTIONAL_EXTERNAL_OR_PYTHON,
        scope=DEPENDENCY_SCOPE_EXTERNAL_TOOL,
        auto_install=False,
        notes="Record actual distribution licences before enabling.",
    ),
    CaptureDependencyAuditItem(
        name="ArchiveBox",
        license="MIT",
        role="local archive",
        decision=DEPENDENCY_DECISION_OPTIONAL_EXTERNAL,
        scope=DEPENDENCY_SCOPE_EXTERNAL_TOOL,
        auto_install=False,
        notes="Docker/WSL/remote/app-native modes remain separately gated.",
    ),
    CaptureDependencyAuditItem(
        name="HRDepartment/archivetoday",
        license="MIT",
        role="archive.today client candidate",
        decision=DEPENDENCY_DECISION_REVIEW,
        scope=DEPENDENCY_SCOPE_REFERENCE_ONLY,
        notes="Small unofficial client; review before use.",
    ),
    CaptureDependencyAuditItem(
        name="obsidian-wayback-archiver",
        license="MIT",
        role="queue/challenge reference",
        decision=DEPENDENCY_DECISION_REVIEW,
        scope=DEPENDENCY_SCOPE_REFERENCE_ONLY,
    ),
    CaptureDependencyAuditItem(
        name="wabarc/wayback",
        license="GPL-3.0",
        role="multi-provider backend",
        decision=DEPENDENCY_DECISION_EXTERNAL_ONLY,
        scope=DEPENDENCY_SCOPE_EXTERNAL_TOOL,
        auto_install=False,
    ),
    CaptureDependencyAuditItem(
        name="archivenow",
        license="MIT",
        role="protocol reference",
        decision=DEPENDENCY_DECISION_REFERENCE,
        scope=DEPENDENCY_SCOPE_REFERENCE_ONLY,
        notes="Assess staleness before any use.",
    ),
    CaptureDependencyAuditItem(
        name="Scoop",
        license="MIT",
        role="high-fidelity WARC/WACZ",
        decision=DEPENDENCY_DECISION_OPTIONAL_EXTERNAL,
        scope=DEPENDENCY_SCOPE_EXTERNAL_TOOL,
        auto_install=False,
    ),
    CaptureDependencyAuditItem(
        name="ArchiveWeb.page",
        license="AGPL-3.0",
        role="manual high-fidelity capture",
        decision=DEPENDENCY_DECISION_EXTERNAL_ONLY,
        scope=DEPENDENCY_SCOPE_EXTERNAL_TOOL,
        auto_install=False,
    ),
    CaptureDependencyAuditItem(
        name="Browsertrix Crawler",
        license="AGPL-3.0-or-later",
        role="crawler",
        decision=DEPENDENCY_DECISION_EXTERNAL_ONLY,
        scope=DEPENDENCY_SCOPE_EXTERNAL_TOOL,
        auto_install=False,
    ),
    CaptureDependencyAuditItem(
        name="Video DownloadHelper installed extension",
        license="reference-only user-supplied material",
        role="architecture reference",
        decision=DEPENDENCY_DECISION_REFERENCE,
        scope=DEPENDENCY_SCOPE_REFERENCE_ONLY,
        auto_install=False,
        notes=(
            "Use observed architecture patterns only; do not copy bundled keys, assets, "
            "translations, profile data, private licence/account data, or unreviewed bulk/minified code."
        ),
    ),
)


def available_capture_dependency_audit_items() -> tuple[CaptureDependencyAuditItem, ...]:
    return CAPTURE_DEPENDENCY_AUDIT_ITEMS


def capture_dependency_audit_to_dict() -> dict[str, Any]:
    return {
        "dependency_count": len(CAPTURE_DEPENDENCY_AUDIT_ITEMS),
        "dependencies": [item.to_dict() for item in CAPTURE_DEPENDENCY_AUDIT_ITEMS],
        "scope": DEPENDENCY_AUDIT_SCOPE,
    }


def dependency_audit_item_by_name(name: str) -> CaptureDependencyAuditItem | None:
    normalized = str(name or "").strip().lower()
    return next(
        (item for item in CAPTURE_DEPENDENCY_AUDIT_ITEMS if item.name.lower() == normalized),
        None,
    )
