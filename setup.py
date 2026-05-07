"""Minimal setup.py for backward compatibility.
All project metadata is defined in pyproject.toml.
"""
import re
from pathlib import Path

from setuptools import setup, find_packages

# Read version from __init__.py (single source of truth)
init_path = Path("skill_advisor") / "__init__.py"
version = re.search(
    r'__version__\s*=\s*["\']([^"\']+)',
    init_path.read_text()
).group(1)

setup(
    version=version,
    packages=find_packages(),
)
