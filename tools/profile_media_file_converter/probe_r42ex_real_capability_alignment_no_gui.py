from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
main=(root/'main.py').read_text(encoding='utf-8', errors='replace')
prof=(root/'profile_media_file_converter_r42eh.py').read_text(encoding='utf-8', errors='replace')
checks={
  'runnable_probe_present':'def _probe_runnable_video_encoders' in prof,
  'runnable_probe_cache_present':'def _runnable_video_encoders_cached' in prof,
  'compiled_not_hw_proof':'compiled encoder list is not treated as GPU usability proof' in prof,
  'av1_hardware_args_present':'elif encoder_impl in {"av1_amf", "av1_nvenc", "av1_qsv", "av1_mf", "av1_vulkan"}' in prof,
  'selection_uses_runnable':'selection_encoders = runnable_encoders or encoders' in prof,
  'encoder_command_aligned_recorded':'encoder_command_aligned' in prof and 'command_encoder_impl' in prof,
  'cog_real_button_retained':'settings_button = ctk.CTkButton(' in main,
  'cog_darker_on_first_paint':'R42EX: use the darker cog colour' in main,
}
print(json.dumps({'schema':'ytce.r42ex.real_capability_alignment_static_probe.v1','checks':checks,'verdict':all(checks.values())}, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
