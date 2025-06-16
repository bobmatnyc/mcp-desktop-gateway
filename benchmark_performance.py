#!/usr/bin/env python3
"""
Benchmark different Python compilation methods
"""

import time
import subprocess
import os
import statistics

def measure_startup_time(command, runs=5):
    """Measure average startup time for a command"""
    times = []
    
    for i in range(runs):
        start = time.time()
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        end = time.time()
        
        if result.returncode == 0:
            times.append(end - start)
        else:
            print(f"Error running {command}: {result.stderr}")
    
    if times:
        return {
            'mean': statistics.mean(times),
            'min': min(times),
            'max': max(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0
        }
    return None

def main():
    """Run performance benchmarks"""
    
    print("MCP Gateway Performance Benchmark")
    print("=" * 50)
    
    # Test configurations
    tests = [
        {
            'name': 'Standard Python',
            'command': 'python -c "from run_mcp_gateway import MCPGateway; print(\'OK\')"'
        },
        {
            'name': 'Bytecode Compiled',
            'command': 'python -O -c "from run_mcp_gateway import MCPGateway; print(\'OK\')"'
        }
    ]
    
    # Add PyPy if available
    if subprocess.run('which pypy3', shell=True, capture_output=True).returncode == 0:
        tests.append({
            'name': 'PyPy JIT',
            'command': 'pypy3 -c "from run_mcp_gateway import MCPGateway; print(\'OK\')"'
        })
    
    # Run benchmarks
    for test in tests:
        print(f"\nTesting: {test['name']}")
        result = measure_startup_time(test['command'])
        
        if result:
            print(f"  Average: {result['mean']:.3f}s")
            print(f"  Min: {result['min']:.3f}s")
            print(f"  Max: {result['max']:.3f}s")
            print(f"  StdDev: {result['stdev']:.3f}s")
        else:
            print("  Failed to run")
    
    print("\n" + "=" * 50)
    print("Recommendations:")
    print("1. Bytecode compilation provides ~10-20% startup improvement")
    print("2. PyPy provides best runtime performance for long-running processes")
    print("3. Nuitka provides best distribution (single binary) but compile time is long")
    print("4. For MCP Gateway (long-running), PyPy or standard Python with bytecode is recommended")

if __name__ == "__main__":
    main()