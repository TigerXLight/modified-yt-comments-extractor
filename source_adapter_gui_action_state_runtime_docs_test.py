from __future__ import annotations

from pathlib import Path


def test_gui_action_state_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_GUI_ACTION_STATE_RUNTIME.md").read_text(encoding="utf-8")
    assert "GUI Action State Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_GUI_ACTION_STATE_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_gui_action_state_runtime_docs()
    print("Source Adapter GUI Action State Runtime docs self-test passed.")
