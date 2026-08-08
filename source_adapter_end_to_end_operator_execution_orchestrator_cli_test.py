import io
from contextlib import redirect_stdout

from source_adapter_end_to_end_operator_execution_orchestrator_cli import main

buf = io.StringIO()
with redirect_stdout(buf):
    code = main(["--json"])
assert code == 0
out = buf.getvalue()
assert '"verified": true' in out
assert "KEYS/ACCOUNTS" in out
print("Source Adapter End-to-End Operator Execution Orchestrator CLI self-test passed.")
