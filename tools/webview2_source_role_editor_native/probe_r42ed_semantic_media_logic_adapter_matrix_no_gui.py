from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_semantic_media_logic_matrix_r42ed import build_semantic_media_logic_adapter_matrix, SOURCE


def main() -> int:
    recolor = "--recolor" in sys.argv
    result = build_semantic_media_logic_adapter_matrix(
        project_root=ROOT,
        source_url=SOURCE,
        output_root=ROOT / "profile_media_live_captures" / "r42ed_semantic_media_logic_adapter_matrix",
        recolor=recolor,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    verdict = result.get("verdict", {})
    required = [
        "comprehension_matrix_defined",
        "adapter_guard_matrix_covers_r42di_to_r42dm",
        "discovery_fallbacks_are_not_silent_substitution",
        "account_channel_device_adapters_explicit_only",
        "no_gui_no_network_safe",
    ]
    if not all(bool(verdict.get(k)) for k in required):
        return 2
    # Payload can be absent in a fresh clone; warn via JSON but keep probe useful.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
