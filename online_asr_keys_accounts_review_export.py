from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from online_asr_keys_accounts_app_state import OnlineASRKeysAccountsAppState
from online_asr_keys_accounts_state_store import (
    OnlineASRKeysAccountsStateStoreResult,
    build_online_asr_keys_accounts_state_store_payloads,
)
from total_export_manifest import ASSET_MANIFEST, ASSET_RAW_SIDECAR, ExportAsset, TotalExportManifest


ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_EXPORT_SCHEMA_VERSION = "online_asr_keys_accounts_review_export_v1"


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


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), separators=(",", ":"), sort_keys=True)


def _sha256(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()


def _metadata_asset(
    *,
    asset_type: str,
    description: str,
    metadata: Mapping[str, Any],
    created_at_utc: str,
) -> ExportAsset:
    encoded = _stable_json(metadata)
    return ExportAsset(
        asset_type=asset_type,
        description=description,
        created_at_utc=created_at_utc,
        sha256=hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        mime_type="application/json",
        size_bytes=len(encoded.encode("utf-8")),
    )


def _safe_payload_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    data = _value_for_dict(payload)
    return {
        "schema_version": ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_EXPORT_SCHEMA_VERSION,
        "payload_sha256": _sha256(data),
        "payload_metadata_only": True,
        "provider_call_allowed_without_user_approval": False,
        "runtime_provider_call_performed": False,
        "credential_value_read": False,
        "plaintext_secret_storage_allowed": False,
        "secret_value_recorded": False,
        "raw_media_payload_included": False,
        "full_local_path_included": False,
        "completed_transcription_claimed": False,
        "payload": data,
    }


@dataclass(frozen=True)
class OnlineASRKeysAccountsReviewExportSummary:
    package_id: str
    selected_provider_id: str
    selected_provider_ready_for_gate_review: bool
    manifest_asset_count: int
    manifest_capture_options: tuple[str, ...]
    state_payload_filenames: tuple[str, ...]
    schema_version: str = ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_EXPORT_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    execution_state: str = "EXECUTION_GATED"
    metadata_only: bool = True
    provider_call_allowed_without_user_approval: bool = False
    runtime_provider_call_performed: bool = False
    credential_value_read: bool = False
    plaintext_secret_storage_allowed: bool = False
    secret_value_recorded: bool = False
    raw_media_payload_included: bool = False
    full_local_path_included: bool = False
    completed_transcription_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    def to_summary_text(self) -> str:
        readiness = "ready for explicit provider-call review" if self.selected_provider_ready_for_gate_review else "needs key/account before provider-call review"
        return "\n".join(
            (
                "Online ASR KEYS/ACCOUNTS review export",
                f"Package ID: {self.package_id}",
                f"Selected provider: {self.selected_provider_id or 'none'} ({readiness})",
                f"Metadata assets: {self.manifest_asset_count}",
                "Review status: USER_REVIEW_REQUIRED",
                "Execution state: EXECUTION_GATED",
                "Provider call allowed without user approval: false",
                "Runtime provider call performed: false",
                "Credential value read: false",
            )
        )


def build_online_asr_keys_accounts_review_manifest(
    *,
    app_state: OnlineASRKeysAccountsAppState,
    package_id: str,
    created_at_utc: str,
    state_payloads: Mapping[str, Mapping[str, Any]] | None = None,
    state_store_result: OnlineASRKeysAccountsStateStoreResult | Mapping[str, Any] | None = None,
    online_asr_gate_summary: Mapping[str, Any] | Any | None = None,
    app_version: str = "",
) -> TotalExportManifest:
    """Build a Total Export manifest for Online ASR KEYS/ACCOUNTS review state.

    This is a metadata-only export view. It links the app-facing KEYS/ACCOUNTS
    state, selected-provider readiness, the state-store bundle payloads, and an
    optional Online ASR execution-gate summary without reading credential values,
    executing a provider call, serializing raw media, exposing full local paths,
    or claiming completed transcription.
    """
    payloads = dict(state_payloads or build_online_asr_keys_accounts_state_store_payloads(app_state))
    assets: list[ExportAsset] = []
    capture_options: list[str] = []

    for filename in sorted(payloads):
        payload = payloads[filename]
        role = filename.removesuffix(".json")
        asset_type = ASSET_MANIFEST if filename.endswith("state_bundle.json") else ASSET_RAW_SIDECAR
        assets.append(
            _metadata_asset(
                asset_type=asset_type,
                description=(
                    f"Online ASR KEYS/ACCOUNTS {role} metadata; "
                    "provider_call_allowed_without_user_approval=false; "
                    "credential_value_read=false; completed_transcription_claimed=false."
                ),
                metadata=_safe_payload_metadata(payload),
                created_at_utc=created_at_utc,
            )
        )
    capture_options.extend(
        (
            "Online ASR KEYS/ACCOUNTS app state metadata",
            "Online ASR provider catalogue metadata",
            "Online ASR selected-provider readiness metadata",
            "Online ASR KEYS/ACCOUNTS state bundle metadata",
        )
    )

    if state_store_result is not None:
        result_metadata = _safe_payload_metadata(_value_for_dict(state_store_result))
        assets.append(
            _metadata_asset(
                asset_type=ASSET_MANIFEST,
                description=(
                    "Online ASR KEYS/ACCOUNTS persisted state-store result metadata; "
                    "full_local_path_included=false."
                ),
                metadata=result_metadata,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Online ASR KEYS/ACCOUNTS persisted state-store result metadata")

    if online_asr_gate_summary is not None:
        gate_metadata = _safe_payload_metadata(_value_for_dict(online_asr_gate_summary))
        assets.append(
            _metadata_asset(
                asset_type=ASSET_RAW_SIDECAR,
                description=(
                    "Online ASR provider-call execution-gate metadata; "
                    "provider_call_allowed_without_user_approval=false."
                ),
                metadata=gate_metadata,
                created_at_utc=created_at_utc,
            )
        )
        capture_options.append("Online ASR execution-gate metadata")

    notes = "\n".join(
        (
            "Online ASR KEYS/ACCOUNTS review manifest metadata only.",
            "Status labels: METADATA_ONLY / LOCAL_ONLY / USER_REVIEW_REQUIRED / EXECUTION_GATED.",
            "No credential values, provider API calls, raw media payloads, full local paths, or completed transcription claims are included.",
            f"Schema: {ONLINE_ASR_KEYS_ACCOUNTS_REVIEW_EXPORT_SCHEMA_VERSION}",
        )
    )
    return TotalExportManifest(
        package_id=package_id,
        created_at_utc=created_at_utc,
        source_urls=[],
        capture_options=sorted(set(capture_options)),
        assets=assets,
        archive_results=[],
        notes=notes,
        app_version=app_version,
    )


def build_online_asr_keys_accounts_review_export_summary(
    *,
    app_state: OnlineASRKeysAccountsAppState,
    manifest: TotalExportManifest,
    state_payload_filenames: Sequence[str] | None = None,
) -> OnlineASRKeysAccountsReviewExportSummary:
    payload_names = tuple(sorted(state_payload_filenames or build_online_asr_keys_accounts_state_store_payloads(app_state)))
    return OnlineASRKeysAccountsReviewExportSummary(
        package_id=manifest.package_id,
        selected_provider_id=app_state.selected_provider.provider_id,
        selected_provider_ready_for_gate_review=app_state.selected_provider_ready_for_gate_review,
        manifest_asset_count=len(manifest.assets),
        manifest_capture_options=tuple(sorted(manifest.capture_options)),
        state_payload_filenames=payload_names,
    )


def online_asr_keys_accounts_review_manifest_to_json(manifest: TotalExportManifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n"


def online_asr_keys_accounts_review_export_summary_to_json(
    summary: OnlineASRKeysAccountsReviewExportSummary,
) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n"
