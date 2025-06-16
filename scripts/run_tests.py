#!/usr/bin/env python3
"""
Script to run tests for MCP Desktop Gateway
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run tests with proper configuration."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Set up environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root / 'src')
    
    # Build pytest command
    pytest_cmd = [
        str(project_root / 'venv' / 'bin' / 'python'),
        '-m', 'pytest'
    ]
    
    # Add arguments passed to this script
    if len(sys.argv) > 1:
        pytest_cmd.extend(sys.argv[1:])
    else:
        # Default: run all tests with verbose output
        pytest_cmd.extend([
            'tests/',
            '-v',
            '--tb=short',
            '--disable-warnings'
        ])
    
    print(f"Running: {' '.join(pytest_cmd)}")
    print(f"Working directory: {project_root}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    print("-" * 60)
    
    # Run pytest
    result = subprocess.run(pytest_cmd, env=env)
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()