from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


PROVIDER_STATUS_TESTED = "tested"
PROVIDER_STATUS_REJECTED = "rejected"
PROVIDER_STATUS_CANDIDATE = "candidate"
PROVIDER_STATUS_BLOCKED = "blocked"
PROVIDER_STATUS_LOCAL_FALLBACK = "local_fallback"
PROVIDER_STATUS_PLANNED = "planned"
PROVIDER_STATUS_UNKNOWN = "unknown"

CREDENTIAL_NONE = "none"
CREDENTIAL_API_KEY = "api_key"
CREDENTIAL_OAUTH = "oauth"
CREDENTIAL_CLOUD_ACCOUNT = "cloud_account"
CREDENTIAL_LOCAL_BINARY = "local_binary"
CREDENTIAL_UNKNOWN = "unknown"

ACCESS_LOCAL_FREE = "local_free"
ACCESS_FREE_TIER_OR_TRIAL = "free_tier_or_trial"
ACCESS_PAID_USAGE = "paid_usage"
ACCESS_BLOCKED_OR_UNAVAILABLE = "blocked_or_unavailable"
ACCESS_UNKNOWN = "unknown"


@dataclass(frozen=True)
class ASRProviderMetadata:
    provider_id: str
    display_name: str
    provider_family: str = ""
    credential_type: str = CREDENTIAL_UNKNOWN
    credentials_required: bool = False
    local_runtime: bool = False
    status: str = PROVIDER_STATUS_UNKNOWN
    best_known_accuracy_percent: Optional[float] = None
    recommended_role: str = ""
    setup_hint: str = ""
    privacy_notes: str = ""
    cost_or_rate_limit_notes: str = ""
    access_limitations: str = ""
    test_connection_supported: bool = False
    notes: str = ""


_ASR_PROVIDER_METADATA = (
    ASRProviderMetadata(
        provider_id="elevenlabs_scribe",
        display_name="ElevenLabs Scribe",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_API_KEY,
        credentials_required=True,
        local_runtime=False,
        status=PROVIDER_STATUS_CANDIDATE,
        best_known_accuracy_percent=84.95,
        recommended_role="Leading optional cloud candidate for draft ASR.",
        setup_hint="Configure an ElevenLabs API key before any future provider integration is used.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Cloud ASR may be quota, rate-limit, and paid-usage dependent.",
        notes="Best tested online result so far, but it still missed some terms and Term QA remains required.",
    ),
    ASRProviderMetadata(
        provider_id="whisper_cpp_vulkan_large_v3_turbo",
        display_name="whisper.cpp Vulkan large-v3-turbo",
        provider_family="local_asr",
        credential_type=CREDENTIAL_LOCAL_BINARY,
        credentials_required=False,
        local_runtime=True,
        status=PROVIDER_STATUS_LOCAL_FALLBACK,
        best_known_accuracy_percent=74.19,
        recommended_role="Best known local/free fallback with phrase prompt.",
        setup_hint="Requires local whisper.cpp Vulkan binary/model setup.",
        privacy_notes="Local runtime keeps audio on the user's machine.",
        cost_or_rate_limit_notes="No cloud API quota; performance depends on local hardware.",
        notes="Best tested no-cloud baseline, but still below the project acceptance threshold on the reference clip.",
    ),
    ASRProviderMetadata(
        provider_id="assemblyai_universal_3_5_pro",
        display_name="AssemblyAI Universal-3.5 Pro",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_API_KEY,
        credentials_required=True,
        status=PROVIDER_STATUS_REJECTED,
        best_known_accuracy_percent=70.97,
        recommended_role="Not recommended based on current benchmark results.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Cloud ASR may be quota, rate-limit, and paid-usage dependent.",
        notes="Default and prompted/keyterms runs stayed below the acceptance threshold.",
    ),
    ASRProviderMetadata(
        provider_id="deepgram_nova_3",
        display_name="Deepgram Nova-3 keyterms",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_API_KEY,
        credentials_required=True,
        status=PROVIDER_STATUS_REJECTED,
        best_known_accuracy_percent=66.67,
        recommended_role="Not recommended based on current benchmark results.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Cloud ASR may be quota, rate-limit, and paid-usage dependent.",
        notes="Keyterms run failed the critical phrase and remained below stronger options.",
    ),
    ASRProviderMetadata(
        provider_id="speechmatics_enhanced",
        display_name="Speechmatics enhanced custom dictionary",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_API_KEY,
        credentials_required=True,
        status=PROVIDER_STATUS_REJECTED,
        best_known_accuracy_percent=65.59,
        recommended_role="Not recommended based on current benchmark results.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Cloud ASR may be quota, rate-limit, and paid-usage dependent.",
        notes="Custom dictionary run found some important terms but failed the critical phrase.",
    ),
    ASRProviderMetadata(
        provider_id="azure_speech",
        display_name="Azure Speech SDK phrase list",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_CLOUD_ACCOUNT,
        credentials_required=True,
        status=PROVIDER_STATUS_REJECTED,
        best_known_accuracy_percent=64.52,
        recommended_role="Not recommended based on current benchmark results.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Cloud ASR may be quota, rate-limit, and paid-usage dependent.",
        notes="en-US and en-GB phrase-list runs produced the same below-threshold result.",
    ),
    ASRProviderMetadata(
        provider_id="google_stt_video_enhanced",
        display_name="Google STT video enhanced phrases",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_API_KEY,
        credentials_required=True,
        status=PROVIDER_STATUS_REJECTED,
        best_known_accuracy_percent=61.29,
        recommended_role="Not recommended based on current benchmark results.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Cloud ASR may be quota, rate-limit, and paid-usage dependent.",
        notes="Best Google run tested, but it missed key glossary terms and the critical phrase.",
    ),
    ASRProviderMetadata(
        provider_id="cohere_transcribe",
        display_name="Cohere Transcribe",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_API_KEY,
        credentials_required=True,
        status=PROVIDER_STATUS_REJECTED,
        best_known_accuracy_percent=58.06,
        recommended_role="Not recommended based on current benchmark results.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Cloud ASR may be quota, rate-limit, and paid-usage dependent.",
        notes="Missed all tracked important terms in the tested run.",
    ),
    ASRProviderMetadata(
        provider_id="google_stt_latest_long",
        display_name="Google STT latest_long phrases",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_API_KEY,
        credentials_required=True,
        status=PROVIDER_STATUS_REJECTED,
        best_known_accuracy_percent=50.54,
        recommended_role="Not recommended based on current benchmark results.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Cloud ASR may be quota, rate-limit, and paid-usage dependent.",
        notes="Performed worse than Google video enhanced and missed key glossary terms.",
    ),
    ASRProviderMetadata(
        provider_id="aws_transcribe_custom_vocabulary",
        display_name="AWS Transcribe custom vocabulary",
        provider_family="cloud_asr",
        credential_type=CREDENTIAL_CLOUD_ACCOUNT,
        credentials_required=True,
        local_runtime=False,
        status=PROVIDER_STATUS_BLOCKED,
        best_known_accuracy_percent=None,
        recommended_role="Possible future retest only if service access becomes available without unwanted billing risk.",
        setup_hint="Requires AWS account/service access and custom vocabulary setup.",
        privacy_notes="Cloud ASR sends audio to the provider and should remain user opt-in.",
        cost_or_rate_limit_notes="Do not upgrade to paid AWS solely for this test unless explicitly approved.",
        access_limitations=(
            "Blocked by SubscriptionRequiredException/service subscription access; "
            "not rejected for transcription quality because no score was produced."
        ),
        notes="S3 setup worked, but CreateVocabulary failed before a transcription job could run.",
    ),
)


def available_asr_provider_metadata() -> tuple[ASRProviderMetadata, ...]:
    return _ASR_PROVIDER_METADATA


def get_asr_provider_metadata(provider_id: str) -> Optional[ASRProviderMetadata]:
    for provider in _ASR_PROVIDER_METADATA:
        if provider.provider_id == provider_id:
            return provider
    return None


def recommended_asr_provider_metadata() -> tuple[ASRProviderMetadata, ...]:
    return tuple(
        provider
        for provider in _ASR_PROVIDER_METADATA
        if provider.status in {PROVIDER_STATUS_CANDIDATE, PROVIDER_STATUS_LOCAL_FALLBACK}
    )


def rejected_asr_provider_metadata() -> tuple[ASRProviderMetadata, ...]:
    return tuple(
        provider
        for provider in _ASR_PROVIDER_METADATA
        if provider.status == PROVIDER_STATUS_REJECTED
    )


def blocked_asr_provider_metadata() -> tuple[ASRProviderMetadata, ...]:
    return tuple(
        provider
        for provider in _ASR_PROVIDER_METADATA
        if provider.status == PROVIDER_STATUS_BLOCKED
    )
