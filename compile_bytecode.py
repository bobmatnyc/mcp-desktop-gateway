#!/usr/bin/env python3
"""
Compile all Python files to bytecode for faster startup
"""

import py_compile
import compileall
import os
import sys

def compile_project():
    """Compile all Python files to bytecode"""
    
    # Compile with optimization level 2 (removes docstrings)
    print("Compiling Python files to bytecode...")
    
    # Compile main files
    files_to_compile = [
        "run_mcp_gateway.py",
        "run_mcp_gateway_simple.py"
    ]
    
    for file in files_to_compile:
        if os.path.exists(file):
            print(f"Compiling {file}...")
            py_compile.compile(file, optimize=2)
    
    # Compile all modules in src
    print("Compiling src directory...")
    compileall.compile_dir(
        "src",
        force=True,
        optimize=2,
        quiet=False
    )
    
    print("Bytecode compilation complete!")
    print("Files are now compiled to .pyc in __pycache__ directories")
    
    # Create startup script that uses compiled bytecode
    startup_script = """#!/usr/bin/env python3
import sys
import os

# Add compiled modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run from compiled bytecode
from __pycache__.run_mcp_gateway import main
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""
    
    with open("mcp_gateway_compiled.py", "w") as f:
        f.write(startup_script)
    
    os.chmod("mcp_gateway_compiled.py", 0o755)
    print("Created mcp_gateway_compiled.py startup script")

if __name__ == "__main__":
    compile_project()