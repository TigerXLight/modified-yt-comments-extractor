from local_asr_capabilities import (
    ASR_ENGINE_WHISPERCPP_VULKAN,
    ASR_RUNNER_WHISPERCPP,
    LocalASRCapabilityInputs,
    acceleration_label,
    build_local_asr_capability_lines,
    capability_lines_contain,
    normalize_gpu_vendor_hint,
    resolve_local_asr_selection,
)


def test_acceleration_labels_separate_cuda_from_generic_gpu() -> None:
    assert acceleration_label("cpu") == "CPU"
    assert acceleration_label("cuda") == "NVIDIA CUDA"
    assert acceleration_label("vulkan") == "Vulkan"


def test_amd_gpu_guidance_requires_real_whispercpp_vulkan_backend() -> None:
    lines = build_local_asr_capability_lines(
        LocalASRCapabilityInputs(
            model_name="large-v3",
            device="cpu",
            compute_type="int8",
            faster_whisper_available=True,
            whispercpp_vulkan_available=False,
            whispercpp_vulkan_binary_detected=True,
            whispercpp_vulkan_model_detected=False,
            gpu_vendor_hint="AMD Radeon RX 5700",
        )
    )

    assert capability_lines_contain(lines, "Engine/backend: faster-whisper")
    assert capability_lines_contain(lines, "Acceleration: CPU")
    assert capability_lines_contain(lines, "large-v3 can be slow on CPU")
    assert capability_lines_contain(lines, "AMD GPU detected")
    assert capability_lines_contain(lines, "whisper.cpp Vulkan binary detected")
    assert capability_lines_contain(lines, "whisper.cpp large-v3 model not detected")
    assert capability_lines_contain(lines, "Benchmark-backed local profile is not fully configured")
    assert not capability_lines_contain(lines, "CUDA appears available")


def test_nvidia_cuda_guidance_is_not_described_as_amd_vulkan() -> None:
    lines = build_local_asr_capability_lines(
        LocalASRCapabilityInputs(
            model_name="small",
            device="cuda",
            compute_type="float16",
            faster_whisper_available=True,
            cuda_available=True,
            cuda_device_name="NVIDIA GeForce RTX Test",
            whispercpp_vulkan_available=False,
        )
    )

    assert capability_lines_contain(lines, "Acceleration: NVIDIA CUDA")
    assert capability_lines_contain(lines, "NVIDIA CUDA acceleration appears available")
    assert capability_lines_contain(lines, "separate from whisper.cpp Vulkan")
    assert not capability_lines_contain(lines, "AMD GPU detected")


def test_cpu_only_guidance_does_not_expose_fake_vulkan_option() -> None:
    lines = build_local_asr_capability_lines(
        {
            "model_name": "medium",
            "device": "cpu",
            "compute_type": "int8",
            "faster_whisper_available": True,
            "whispercpp_vulkan_available": False,
        }
    )

    assert capability_lines_contain(lines, "CPU acceleration selected")
    assert capability_lines_contain(lines, "selecting a model does not select Vulkan")
    assert not capability_lines_contain(lines, "Benchmark-backed local profile detected")


def test_configured_whispercpp_vulkan_is_reported_only_when_detected() -> None:
    lines = build_local_asr_capability_lines(
        LocalASRCapabilityInputs(
            selection=resolve_local_asr_selection(
                {
                    "engine": "whispercpp_vulkan",
                    "model_name": "large-v3",
                    "device": "vulkan",
                    "compute_type": "",
                }
            ),
            faster_whisper_available=True,
            whispercpp_vulkan_available=True,
            gpu_vendor_hint="AMD Radeon",
        )
    )

    assert capability_lines_contain(lines, "Selected configuration")
    assert capability_lines_contain(lines, "Engine/backend: whisper.cpp")
    assert capability_lines_contain(lines, "Acceleration: Vulkan")
    assert capability_lines_contain(lines, "Model: large-v3")
    assert capability_lines_contain(lines, "Compute type: Not applicable")
    assert capability_lines_contain(lines, "Resolved runner: asr_whispercpp")
    assert capability_lines_contain(lines, "faster-whisper backend: Installed")
    assert not capability_lines_contain(lines, "Selected acceleration: CPU")
    assert not capability_lines_contain(lines, "Selected compute type: whisper.cpp")
    assert capability_lines_contain(lines, "whisper.cpp Vulkan binary detected")
    assert capability_lines_contain(lines, "whisper.cpp large-v3 model detected")
    assert capability_lines_contain(
        lines,
        "Benchmark-backed local profile detected: whisper.cpp / Vulkan / large-v3",
    )
    assert not capability_lines_contain(lines, "requires a configured whisper.cpp Vulkan")


def test_gpu_vendor_hint_normalization() -> None:
    assert normalize_gpu_vendor_hint("AMD Radeon RX 5700") == "amd"
    assert normalize_gpu_vendor_hint("NVIDIA GeForce RTX") == "nvidia"
    assert normalize_gpu_vendor_hint("Intel Arc") == "intel"
    assert normalize_gpu_vendor_hint("Generic Display") == ""


def test_resolved_selection_keeps_compute_type_out_of_whispercpp_profile() -> None:
    selection = resolve_local_asr_selection(
        {
            "engine": "whispercpp_vulkan",
            "model_name": "large-v3",
            "device": "vulkan",
            "compute_type": "",
        }
    )

    assert selection.engine_id == ASR_ENGINE_WHISPERCPP_VULKAN
    assert selection.acceleration == "vulkan"
    assert selection.model_name == "large-v3"
    assert selection.faster_whisper_compute_type is None
    assert selection.resolved_runner == ASR_RUNNER_WHISPERCPP


def run_self_test() -> None:
    test_acceleration_labels_separate_cuda_from_generic_gpu()
    test_amd_gpu_guidance_requires_real_whispercpp_vulkan_backend()
    test_nvidia_cuda_guidance_is_not_described_as_amd_vulkan()
    test_cpu_only_guidance_does_not_expose_fake_vulkan_option()
    test_configured_whispercpp_vulkan_is_reported_only_when_detected()
    test_gpu_vendor_hint_normalization()
    test_resolved_selection_keeps_compute_type_out_of_whispercpp_profile()


if __name__ == "__main__":
    run_self_test()
    print("local_asr_capabilities_test.py: OK")
