"""Pytest conftest to make repository importable during tests."""
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    # Insert at front so local package imports resolve
    sys.path.insert(0, str(REPO_ROOT))
