import subprocess
import sys
from pathlib import Path


def test_contract_checker_passes():
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run([sys.executable, str(root / "scripts/check_task_review_contract.py")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
