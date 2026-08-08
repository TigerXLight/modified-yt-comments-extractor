import io
from contextlib import redirect_stdout

from source_adapter_browser_capture_execution_backend_cli import main

buf = io.StringIO()
with redirect_stdout(buf):
    code = main(["--json"])
assert code == 0
out = buf.getvalue()
assert '"verified": true' in out
assert "KEYS/ACCOUNTS" in out
print("Source Adapter Browser Capture Execution Backend CLI self-test passed.")
