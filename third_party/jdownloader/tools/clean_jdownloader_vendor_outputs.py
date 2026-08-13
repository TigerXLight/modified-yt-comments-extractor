from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TARGETS = (
    ROOT / "third_party" / "jdownloader" / "bridge" / "build",
)


def main() -> int:
    for target in TARGETS:
        if target.exists():
            shutil.rmtree(target)
            print(f"removed {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
