import io
from contextlib import redirect_stdout
from source_adapter_production_runtime_bundle_closeout_cli import main
buf = io.StringIO()
with redirect_stdout(buf):
    code = main(["--json"])
assert code == 0
out = buf.getvalue()
assert '"verified": true' in out
assert "KEYS/ACCOUNTS" in out
print("Source Adapter Production Runtime Bundle Closeout CLI self-test passed.")
