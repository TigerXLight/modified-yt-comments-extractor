import io
from contextlib import redirect_stdout

from source_adapter_gui_live_execution_panel_wiring_cli import main

buf = io.StringIO()
with redirect_stdout(buf):
    code = main(["--json"])
assert code == 0
out = buf.getvalue()
assert '"verified": true' in out
assert "KEYS/ACCOUNTS" in out
print("Source Adapter GUI Live Execution Panel Wiring CLI self-test passed.")
