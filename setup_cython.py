"""
Cython compilation setup for MCP Gateway
Compiles Python modules to C extensions for better performance
"""

from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize
import os
import sys

# Define which modules to compile
modules_to_compile = [
    "src/core/registry.py",
    "src/core/config.py",
    "src/core/base_connector.py",
    "src/core/models.py",
    "src/core/resource_models.py",
    # Don't compile the main entry points or files with dynamic imports
]

# Create extension modules
extensions = []
for module_path in modules_to_compile:
    module_name = module_path.replace("/", ".").replace("\\", ".").replace(".py", "")
    extensions.append(
        Extension(
            module_name,
            [module_path],
            extra_compile_args=["-O3"] if sys.platform != "win32" else [],
        )
    )

setup(
    name="mcp-gateway-compiled",
    version="1.0.0",
    packages=find_packages(),
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': "3",
            'always_allow_keywords': True,
            'embedsignature': True,
            'boundscheck': False,
            'wraparound': False,
        }
    ),
    python_requires=">=3.8",
)

# Build command: python setup_cython.py build_ext --inplace