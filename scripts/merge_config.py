#!/usr/bin/env python3
"""
Merge MCP Gateway configuration with existing Claude Desktop config.
Only replaces py_mcp_bridge/eva-mcp-bridge entries, preserving other services.
"""

import json
import sys
import os
from pathlib import Path


def load_json(filepath):
    """Load JSON from file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}", file=sys.stderr)
        return None


def merge_configs(current_config, new_server_config, service_names_to_replace):
    """
    Merge new server config with current config.
    Replaces any services matching the names in service_names_to_replace.
    """
    if not current_config:
        current_config = {"mcpServers": {}}
    
    if "mcpServers" not in current_config:
        current_config["mcpServers"] = {}
    
    # Remove old service entries
    for name in service_names_to_replace:
        if name in current_config["mcpServers"]:
            del current_config["mcpServers"][name]
    
    # Add new service
    current_config["mcpServers"].update(new_server_config)
    
    return current_config


def main():
    if len(sys.argv) < 3:
        print("Usage: merge_config.py <current_config> <new_server_config> [service_names_to_replace...]", file=sys.stderr)
        sys.exit(1)
    
    current_config_path = sys.argv[1]
    new_server_config_path = sys.argv[2]
    service_names_to_replace = sys.argv[3:] if len(sys.argv) > 3 else ["py_mcp_bridge", "eva-mcp-bridge", "py-mcp-bridge"]
    
    # Load configs
    current_config = load_json(current_config_path) if os.path.exists(current_config_path) else {"mcpServers": {}}
    new_server_data = load_json(new_server_config_path)
    
    if not new_server_data or "mcpServers" not in new_server_data:
        print("Error: Invalid server config format", file=sys.stderr)
        sys.exit(1)
    
    # Merge configs
    merged = merge_configs(current_config, new_server_data["mcpServers"], service_names_to_replace)
    
    # Output merged config
    print(json.dumps(merged, indent=2))


if __name__ == "__main__":
    main()