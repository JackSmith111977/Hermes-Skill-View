"""Minimal setup.py for backward compatibility.
All project metadata is defined in pyproject.toml.
Version is handled by setuptools-scm via [tool.setuptools_scm].
"""
from setuptools import setup, find_packages

setup(
    packages=find_packages(),
)
