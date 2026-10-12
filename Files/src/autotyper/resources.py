"""Locate bundled resources both in development and inside a PyInstaller bundle."""

import sys
from pathlib import Path


def project_root():
    # src/autotyper/resources.py -> project root is two levels above the package
    return Path(__file__).resolve().parents[2]


def resource_path(*parts):
    frozen_base = getattr(sys, "_MEIPASS", None)
    base = Path(frozen_base) if frozen_base else project_root()
    return base.joinpath(*parts)
