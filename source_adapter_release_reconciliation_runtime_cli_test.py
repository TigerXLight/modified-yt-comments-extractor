import io
from contextlib import redirect_stdout
from source_adapter_release_reconciliation_runtime_cli import main
buf = io.StringIO()
with redirect_stdout(buf):
    code = main(["--json"])
assert code == 0
out = buf.getvalue()
assert '"verified": true' in out
assert "KEYS/ACCOUNTS" in out
print("Source Adapter Release Reconciliation Runtime CLI self-test passed.")
