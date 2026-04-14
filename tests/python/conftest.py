"""Shared pytest fixtures and path setup.

Adds the project root to sys.path so test modules can import
`scripts._slug`, `scripts.derive_edges`, etc. without installing
the project as a package.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
