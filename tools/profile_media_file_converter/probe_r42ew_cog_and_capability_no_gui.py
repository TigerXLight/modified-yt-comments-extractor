from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8',errors='replace')
prof=(ROOT/'profile_media_file_converter_r42eh.py').read_text(encoding='utf-8',errors='replace')
checks={
 'cog_is_sibling_ctk_button': 'settings_button = ctk.CTkButton(' in main and 'raw-label overlay' in main,
 'cog_no_duplicate_button1': 'settings_button.bind("<Button-1>", lambda _event: settings_command())' not in main,
 'compression_playback_default_1x_retained': '"playback_speed": "1.0x"' in main,
 'advanced_tabs_retained': 'CTkSegmentedButton' in main and 'Image resolution' in main and 'Video resolution' in main,
 'expanded_encoder_detection': all(x in prof for x in ['h264_mf','hevc_mf','librav1e','libsvt_av1']),
 'remux_copy_retained': 'normal conversion prefers remux/copy' in prof and 'stream_copy' in prof,
 'dynamic_matcher_retained': '_select_optimised_video_strategy' in prof,
}
print(json.dumps({'schema':'ytce.r42ew.cog_capability_static_probe.v1','checks':checks,'verdict':all(checks.values())},indent=2))
sys.exit(0 if all(checks.values()) else 1)
