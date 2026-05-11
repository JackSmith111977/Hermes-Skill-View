#!/usr/bin/env python3
"""Set static version in pyproject.toml for release builds."""
import re
import sys
from pathlib import Path

version = sys.argv[1] if len(sys.argv) > 1 else "0.0.0"
pyproject = Path("pyproject.toml")
content = pyproject.read_text()

# Replace dynamic version with static version
content = content.replace('dynamic = ["version"]', f'version = "{version}"')

# Remove setuptools_scm config
content = re.sub(
    r'\[tool\.setuptools_scm\].*?(?=\n\[|$)',
    '',
    content,
    flags=re.DOTALL
)

pyproject.write_text(content)
print(f"✅ Set static version: {version}")
