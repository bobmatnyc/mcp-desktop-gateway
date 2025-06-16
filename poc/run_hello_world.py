#!/usr/bin/env python3
"""
Run script for MCP Gateway Hello World POC
Provides startup diagnostics and error handling
"""

import sys
import os
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Error: Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_mcp_package():
    """Check if mcp package is installed"""
    try:
        import mcp
        print("✓ MCP package installed")
        return True
    except ImportError:
        print("❌ Error: MCP package not installed")
        print("  Run: pip install mcp")
        return False

def create_claude_config():
    """Create example Claude Desktop configuration"""
    config = {
        "mcpServers": {
            "mcp-gateway-hello-world": {
                "command": "python",
                "args": [
                    str(Path(__file__).parent / "hello_world_poc.py")
                ],
                "env": {
                    "PYTHONPATH": str(Path(__file__).parent.parent / "mcp-bridge" / "src")
                }
            }
        }
    }
    
    config_path = Path(__file__).parent / "claude_desktop_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✓ Created Claude Desktop config: {config_path}")
    return config_path

def main():
    """Main entry point"""
    print("=== MCP Gateway Hello World POC Launcher ===\n")
    
    # Run checks
    checks_passed = True
    
    if not check_python_version():
        checks_passed = False
    
    if not check_mcp_package():
        checks_passed = False
    
    if not checks_passed:
        print("\n❌ Pre-flight checks failed. Please fix the issues above.")
        sys.exit(1)
    
    # Create Claude config if it doesn't exist
    config_path = Path(__file__).parent / "claude_desktop_config.json"
    if not config_path.exists():
        create_claude_config()
    
    print("\n✅ All checks passed!")
    print("\n" + "="*50)
    print("Starting MCP Gateway Hello World POC...")
    print("="*50 + "\n")
    
    # Add instructions
    print("📋 Quick Setup Instructions:")
    print(f"1. Copy the configuration from: {config_path}")
    print("2. Add it to your Claude Desktop config")
    print("3. Restart Claude Desktop")
    print("4. Look for 'mcp-gateway-hello-world' in Claude\n")
    
    print("🚀 Launching server...\n")
    
    # Run the POC
    poc_script = Path(__file__).parent / "hello_world_poc.py"
    try:
        subprocess.run([sys.executable, str(poc_script)], check=True)
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped gracefully")
    except subprocess.CalledProcessError as e:
        print(f"\n\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()