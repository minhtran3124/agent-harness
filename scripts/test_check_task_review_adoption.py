import subprocess
import sys
from pathlib import Path


def test_adoption_check_passes():
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run([sys.executable, "scripts/check_task_review_adoption.py"], cwd=root, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
