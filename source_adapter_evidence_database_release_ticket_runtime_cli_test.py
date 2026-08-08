import json
import subprocess
import sys
import tempfile

cmd = [sys.executable, "source_adapter_evidence_database_release_ticket_runtime_cli.py", "--verify", "--json"]
proc = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE)
data = json.loads(proc.stdout)
assert data["verification"]["verified"], data
with tempfile.TemporaryDirectory() as tmp:
    proc = subprocess.run([sys.executable, "source_adapter_evidence_database_release_ticket_runtime_cli.py", "--output-dir", tmp, "--json"], check=True, text=True, stdout=subprocess.PIPE)
    data = json.loads(proc.stdout)
    assert data["store"]["store_status"] == "STORED", data
print("Source Adapter Evidence Database Release Ticket Runtime CLI self-test passed.")
