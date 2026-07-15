import asr_quality_policy


def _with_fake_detection(env, profile, func):
    original_env = asr_quality_policy.detect_asr_environment
    original_profile = asr_quality_policy.detect_benchmarked_whispercpp_vulkan_profile
    asr_quality_policy.detect_asr_environment = lambda: dict(env)
    asr_quality_policy.detect_benchmarked_whispercpp_vulkan_profile = lambda: dict(profile)
    try:
        return func()
    finally:
        asr_quality_policy.detect_asr_environment = original_env
        asr_quality_policy.detect_benchmarked_whispercpp_vulkan_profile = original_profile


def _base_env():
    return {
        "cpu_count": 8,
        "gpu_names": [],
        "has_amd_hint": False,
        "has_intel_gpu_hint": False,
        "cuda_available": False,
        "cuda_device_name": "",
        "directml_available": False,
    }


def test_benchmarked_whispercpp_vulkan_profile_is_recommended_when_configured() -> None:
    def run():
        return asr_quality_policy.build_auto_quality_recommendation(
            {"model_name": "small", "device": "cpu", "compute_type": "int8"}
        )

    env = _base_env()
    env.update({"gpu_names": ["AMD Radeon RX 5700"], "has_amd_hint": True})
    profile = {
        "binary_detected": True,
        "model_detected": True,
        "configured": True,
    }
    lines = _with_fake_detection(env, profile, run)
    text = "\n".join(lines)

    assert "Benchmark-backed local profile detected: whisper.cpp / Vulkan / large-v3" in text
    assert "Benchmarked local acceleration uses whisper.cpp / Vulkan / large-v3" in text
    assert "Best current local path: faster-whisper" not in text
    assert "small is a good default" not in text
    assert "Recommended default" not in text


def test_cuda_is_reported_as_separate_from_benchmarked_vulkan_profile() -> None:
    def run():
        return asr_quality_policy.build_auto_quality_recommendation(
            {"model_name": "large-v3", "device": "cuda", "compute_type": "float16"}
        )

    env = _base_env()
    env.update(
        {
            "gpu_names": ["NVIDIA GeForce RTX Test"],
            "cuda_available": True,
            "cuda_device_name": "NVIDIA GeForce RTX Test",
        }
    )
    profile = {
        "binary_detected": False,
        "model_detected": False,
        "configured": False,
    }
    lines = _with_fake_detection(env, profile, run)
    text = "\n".join(lines)

    assert "NVIDIA/CUDA path available: NVIDIA GeForce RTX Test" in text
    assert "CUDA is a separate faster-whisper path" in text
    assert "Benchmark-backed local profile is not fully configured: whisper.cpp / Vulkan / large-v3" in text
    assert "Best current local path" not in text


def run_self_test() -> None:
    test_benchmarked_whispercpp_vulkan_profile_is_recommended_when_configured()
    test_cuda_is_reported_as_separate_from_benchmarked_vulkan_profile()


if __name__ == "__main__":
    run_self_test()
    print("asr_quality_policy_test.py: OK")
