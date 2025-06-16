#!/usr/bin/env python3
"""
Test MCP service functionality by sending JSON-RPC messages via stdio.
"""

import json
import subprocess
import sys
import time
import os
from pathlib import Path


class MCPServiceTester:
    def __init__(self, command, args=None, env=None, cwd=None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.cwd = cwd
        self.process = None
        
    def start(self):
        """Start the MCP service process."""
        cmd = [self.command] + self.args
        
        # Merge environment variables
        process_env = os.environ.copy()
        process_env.update(self.env)
        
        # Set test mode for npm CLI wrapper
        if 'mcp-desktop-gateway' in cmd[0]:
            process_env['MCP_TEST_MODE'] = '1'
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=process_env,
            text=True,
            bufsize=0
        )
        
        # Give the service time to start
        time.sleep(0.5)
        
        # Check if process is still running
        if self.process.poll() is not None:
            stderr = self.process.stderr.read()
            raise RuntimeError(f"Service failed to start: {stderr}")
            
    def send_request(self, method, params=None, timeout=10):
        """Send a JSON-RPC request and get response."""
        import select
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str)
        self.process.stdin.flush()
        
        # Wait for response with timeout
        ready, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not ready:
            raise RuntimeError(f"Timeout waiting for response to {method}")
            
        # Read response
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from service")
            
        return json.loads(response_line)
        
    def send_notification(self, method, params=None):
        """Send a JSON-RPC notification (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        notification_str = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_str)
        self.process.stdin.flush()
        
    def stop(self):
        """Stop the service process."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            

def test_mcp_service(config_path):
    """Test an MCP service from Claude Desktop config."""
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    if "mcpServers" not in config:
        print("❌ No MCP servers configured")
        return False
        
    all_passed = True
    
    for server_name, server_config in config["mcpServers"].items():
        print(f"\n🔍 Testing {server_name}...")
        
        try:
            # Create tester
            tester = MCPServiceTester(
                command=server_config["command"],
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
                cwd=server_config.get("cwd")
            )
            
            # Start service
            print(f"   Starting service...")
            tester.start()
            
            # Test initialize
            print(f"   Testing initialize...")
            response = tester.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-test",
                    "version": "1.0.0"
                }
            })
            
            if "error" in response:
                print(f"   ❌ Initialize failed: {response['error']}")
                all_passed = False
            else:
                print(f"   ✅ Initialize successful")
                
                # Send notifications/initialized after init
                tester.send_notification("notifications/initialized")
                
                # Test tools/list
                print(f"   Testing tools/list...")
                response = tester.send_request("tools/list")
                
                if "error" in response:
                    print(f"   ❌ Tools list failed: {response['error']}")
                    all_passed = False
                else:
                    tools = response.get("result", {}).get("tools", [])
                    print(f"   ✅ Found {len(tools)} tools")
                    
                    # If it's mcp-gateway, test hello_world tool
                    if server_name == "mcp-gateway" and any(t["name"] == "hello_world" for t in tools):
                        print(f"   Testing hello_world tool...")
                        response = tester.send_request("tools/call", {
                            "name": "hello_world",
                            "arguments": {"name": "Test"}
                        })
                        
                        if "error" in response:
                            print(f"   ❌ Tool call failed: {response['error']}")
                            all_passed = False
                        else:
                            result = response.get("result", {})
                            print(f"   ✅ Tool call successful: {result}")
            
            # Stop service
            tester.stop()
            print(f"   ✅ {server_name} passed all tests")
            
        except Exception as e:
            print(f"   ❌ {server_name} failed: {str(e)}")
            all_passed = False
            if tester:
                try:
                    tester.stop()
                except:
                    pass
    
    return all_passed


def test_specific_service(service_name, command, args=None, env=None, cwd=None):
    """Test a specific MCP service configuration."""
    print(f"🔍 Testing {service_name}...")
    
    try:
        tester = MCPServiceTester(command, args, env, cwd)
        
        # Start service
        print(f"   Starting service...")
        tester.start()
        
        # Test initialize
        print(f"   Testing initialize...")
        response = tester.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-test",
                "version": "1.0.0"
            }
        })
        
        if "error" in response:
            print(f"   ❌ Initialize failed: {response['error']}")
            return False
            
        print(f"   ✅ Initialize successful")
        
        # Send notifications/initialized after init
        tester.send_notification("notifications/initialized")
        
        # Test tools/list
        print(f"   Testing tools/list...")
        response = tester.send_request("tools/list")
        
        if "error" in response:
            print(f"   ❌ Tools list failed: {response['error']}")
            return False
            
        tools = response.get("result", {}).get("tools", [])
        print(f"   ✅ Found {len(tools)} tools")
        
        # Stop service
        tester.stop()
        print(f"   ✅ {service_name} passed all tests")
        return True
        
    except Exception as e:
        print(f"   ❌ {service_name} failed: {str(e)}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  test_mcp_service.py config <config_file>")
        print("  test_mcp_service.py service <name> <command> [args...]")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "config":
        # Test all services in a config file
        config_path = sys.argv[2]
        success = test_mcp_service(config_path)
        sys.exit(0 if success else 1)
        
    elif mode == "service":
        # Test a specific service
        if len(sys.argv) < 4:
            print("Usage: test_mcp_service.py service <name> <command> [args...]")
            sys.exit(1)
            
        service_name = sys.argv[2]
        command = sys.argv[3]
        args = sys.argv[4:] if len(sys.argv) > 4 else []
        
        success = test_specific_service(service_name, command, args)
        sys.exit(0 if success else 1)
        
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()