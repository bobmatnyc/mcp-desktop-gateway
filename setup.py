#!/usr/bin/env python3
"""
Setup script for mcp-desktop-gateway.
This file exists for compatibility with older pip versions.
Configuration is primarily in pyproject.toml.
"""

from setuptools import setup, find_packages
import os

# Read version from VERSION file
version_file = os.path.join(os.path.dirname(__file__), 'VERSION')
if os.path.exists(version_file):
    with open(version_file, 'r') as f:
        version = f.read().strip()
else:
    version = "1.0.0"

setup(
    name="mcp-desktop-gateway",
    version=version,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "mcp>=1.9.3",
        "pydantic>=2.11.5", 
        "PyYAML>=6.0.2",
    ],
    entry_points={
        "console_scripts": [
            # Note: The actual scripts need to be refactored to have proper entry points
            # For now, installation will include the scripts but they need to be run directly
        ],
    },
)