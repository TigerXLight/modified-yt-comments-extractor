import io
from contextlib import redirect_stdout

from source_adapter_release_file_delivery_backend_cli import main

buf = io.StringIO()
with redirect_stdout(buf):
    code = main(["--json"])
assert code == 0
out = buf.getvalue()
assert '"verified": true' in out
assert "KEYS/ACCOUNTS" in out
print("Source Adapter Release File Delivery Backend CLI self-test passed.")
