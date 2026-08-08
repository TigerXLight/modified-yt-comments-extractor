import io
from contextlib import redirect_stdout
from source_adapter_archive_closeout_runtime_cli import main
buf = io.StringIO()
with redirect_stdout(buf):
    code = main(["--json"])
assert code == 0
out = buf.getvalue()
assert '"verified": true' in out
assert "KEYS/ACCOUNTS" in out
print("Source Adapter Archive Closeout Runtime CLI self-test passed.")
