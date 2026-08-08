from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping


SOURCE_EXECUTION_BRIDGE_RESULTS_SCHEMA_VERSION = "source_execution_bridge_results_v1"


class ExecutionBridgeImplementationStatus(str, Enum):
    IMPLEMENTED = "implemented"
    FIXTURE_TESTED = "fixture_tested"
    MOCKED_SUBPROCESS_TESTED = "mocked_subprocess_tested"
    FAKE_HTTP_TESTED = "fake_http_tested"
    APPROVAL_GATED = "approval_gated"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(_value_for_dict(value), sort_keys=True, separators=(",", ":"))


def _sha16(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SourceExecutionBridgeResultRow:
    bridge_id: str
    label: str
    implementation_statuses: tuple[ExecutionBridgeImplementationStatus, ...]
    local_fixture_tested: bool
    mocked_subprocess_tested: bool = False
    fake_http_tested: bool = False
    writes_local_artifacts: bool = False
    approval_required_for_live_or_destructive_execution: bool = True
    external_network_performed: bool = False
    browser_live_site_performed: bool = False
    real_provider_call_performed: bool = False
    real_user_file_movement_performed: bool = False
    module_refs: tuple[str, ...] = ()
    test_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceExecutionBridgeResults:
    result_id: str
    rows: tuple[SourceExecutionBridgeResultRow, ...]
    no_external_sites_accessed: bool = True
    no_credentials_used: bool = True
    no_asr_jobs_run: bool = True
    no_user_evidence_files_moved: bool = True
    schema_version: str = SOURCE_EXECUTION_BRIDGE_RESULTS_SCHEMA_VERSION

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def local_fixture_tested_count(self) -> int:
        return sum(1 for row in self.rows if row.local_fixture_tested)

    @property
    def mocked_subprocess_tested_count(self) -> int:
        return sum(1 for row in self.rows if row.mocked_subprocess_tested)

    @property
    def fake_http_tested_count(self) -> int:
        return sum(1 for row in self.rows if row.fake_http_tested)

    @property
    def local_artifact_writer_count(self) -> int:
        return sum(1 for row in self.rows if row.writes_local_artifacts)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["row_count"] = self.row_count
        data["local_fixture_tested_count"] = self.local_fixture_tested_count
        data["mocked_subprocess_tested_count"] = self.mocked_subprocess_tested_count
        data["fake_http_tested_count"] = self.fake_http_tested_count
        data["local_artifact_writer_count"] = self.local_artifact_writer_count
        return data


def build_source_execution_bridge_results() -> SourceExecutionBridgeResults:
    rows = (
        SourceExecutionBridgeResultRow(
            bridge_id="local_browser_execution",
            label="Local browser/screenshot/article/comments/livechat execution bridge",
            implementation_statuses=(
                ExecutionBridgeImplementationStatus.IMPLEMENTED,
                ExecutionBridgeImplementationStatus.FIXTURE_TESTED,
            ),
            local_fixture_tested=True,
            writes_local_artifacts=True,
            module_refs=("source_local_browser_execution.py",),
            test_refs=("source_local_browser_execution_test.py",),
        ),
        SourceExecutionBridgeResultRow(
            bridge_id="media_download_mux_execution",
            label="Media local copy/download and FFmpeg/yt-dlp execution bridge",
            implementation_statuses=(
                ExecutionBridgeImplementationStatus.IMPLEMENTED,
                ExecutionBridgeImplementationStatus.FIXTURE_TESTED,
                ExecutionBridgeImplementationStatus.MOCKED_SUBPROCESS_TESTED,
                ExecutionBridgeImplementationStatus.APPROVAL_GATED,
            ),
            local_fixture_tested=True,
            mocked_subprocess_tested=True,
            writes_local_artifacts=True,
            module_refs=("source_media_execution_bridge.py", "capture_media_download.py"),
            test_refs=("source_media_execution_bridge_test.py", "capture_media_download_test.py"),
        ),
        SourceExecutionBridgeResultRow(
            bridge_id="archive_provider_archivebox_execution",
            label="Archive provider fake-client and ArchiveBox subprocess execution bridge",
            implementation_statuses=(
                ExecutionBridgeImplementationStatus.IMPLEMENTED,
                ExecutionBridgeImplementationStatus.FAKE_HTTP_TESTED,
                ExecutionBridgeImplementationStatus.MOCKED_SUBPROCESS_TESTED,
                ExecutionBridgeImplementationStatus.APPROVAL_GATED,
            ),
            local_fixture_tested=True,
            mocked_subprocess_tested=True,
            fake_http_tested=True,
            module_refs=("source_archive_execution_bridge.py",),
            test_refs=("source_archive_execution_bridge_test.py",),
        ),
        SourceExecutionBridgeResultRow(
            bridge_id="offline_evidence_bundle_writer",
            label="Offline compressed evidence bundle writer",
            implementation_statuses=(
                ExecutionBridgeImplementationStatus.IMPLEMENTED,
                ExecutionBridgeImplementationStatus.FIXTURE_TESTED,
            ),
            local_fixture_tested=True,
            writes_local_artifacts=True,
            module_refs=("source_offline_bundle_writer.py",),
            test_refs=("source_offline_bundle_writer_test.py",),
        ),
        SourceExecutionBridgeResultRow(
            bridge_id="evidence_movement_executor",
            label="Approval-gated evidence movement executor",
            implementation_statuses=(
                ExecutionBridgeImplementationStatus.IMPLEMENTED,
                ExecutionBridgeImplementationStatus.FIXTURE_TESTED,
                ExecutionBridgeImplementationStatus.APPROVAL_GATED,
            ),
            local_fixture_tested=True,
            writes_local_artifacts=True,
            module_refs=("evidence_movement_approval.py",),
            test_refs=("evidence_movement_approval_test.py",),
        ),
        SourceExecutionBridgeResultRow(
            bridge_id="source_url_files_app_bridge",
            label="Source URL/FILES app-facing state bridge",
            implementation_statuses=(
                ExecutionBridgeImplementationStatus.IMPLEMENTED,
                ExecutionBridgeImplementationStatus.FIXTURE_TESTED,
            ),
            local_fixture_tested=True,
            module_refs=("source_url_files_bridge.py",),
            test_refs=("source_url_files_bridge_test.py",),
        ),
    )
    return SourceExecutionBridgeResults(
        result_id="source_execution_bridge_results_" + _sha16([row.to_dict() for row in rows]),
        rows=rows,
    )


def source_execution_bridge_results_to_json(results: SourceExecutionBridgeResults) -> str:
    return json.dumps(results.to_dict(), indent=2, sort_keys=True)

