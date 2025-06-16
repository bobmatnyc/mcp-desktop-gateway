"""
Auto-start functionality for Unified Backend
Ensures the backend is running when needed
"""

import asyncio
import logging
import os
import time
from typing import Optional, Tuple
import aiohttp
import psutil

logger = logging.getLogger(__name__)


class UnifiedBackendAutoStarter:
    """
    Manages automatic starting of the unified backend server
    """
    
    def __init__(self, port_range: Tuple[int, int] = (3000, 3003)):
        self.port_range = port_range
        self._server_process = None
        self._server_url = None
        self._last_check = 0
        self._check_interval = 5  # seconds
        
    async def ensure_running(self) -> str:
        """
        Ensure the unified backend is running, start it if not
        Returns the base URL of the running server
        """
        # Check if we recently verified the server
        current_time = time.time()
        if self._server_url and (current_time - self._last_check) < self._check_interval:
            return self._server_url
        
        # Check if server is already running
        server_url = await self._find_running_server()
        if server_url:
            self._server_url = server_url
            self._last_check = current_time
            logger.info(f"Found existing unified backend at {server_url}")
            return server_url
        
        # Server not running, start it
        logger.info("Unified backend not found, starting...")
        server_url = await self._start_server()
        if server_url:
            self._server_url = server_url
            self._last_check = current_time
            logger.info(f"Started unified backend at {server_url}")
            return server_url
        
        raise RuntimeError("Failed to start unified backend server")
    
    async def _find_running_server(self) -> Optional[str]:
        """Check if a unified backend is already running"""
        async with aiohttp.ClientSession() as session:
            for port in range(self.port_range[0], self.port_range[1] + 1):
                url = f"http://localhost:{port}"
                try:
                    # Check root endpoint to verify it's the unified backend
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=1)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # Check if it's the unified backend (not just OAuth server)
                            if data.get('service') == 'MCP Bridge Unified Backend':
                                return url
                except:
                    continue
        return None
    
    async def _start_server(self) -> Optional[str]:
        """Start the unified backend server as a subprocess"""
        import subprocess
        import sys
        
        # Build command to start the server
        python_path = sys.executable
        
        # Use module invocation instead of script
        cmd = [python_path, '-m', 'src.unified_backend.main', '--mode', 'backend']
        
        # Start the server process
        try:
            # Use subprocess.Popen for non-blocking start
            self._server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            
            # Wait for server to start (with timeout)
            start_time = time.time()
            timeout = 10  # seconds
            
            while time.time() - start_time < timeout:
                server_url = await self._find_running_server()
                if server_url:
                    return server_url
                await asyncio.sleep(0.5)
            
            # Timeout - check if process is still running
            if self._server_process.poll() is not None:
                # Process exited
                stdout, stderr = self._server_process.communicate()
                logger.error(f"Server process exited: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return None
        
        return None
    
    def shutdown(self):
        """Shutdown the server if we started it"""
        if self._server_process and self._server_process.poll() is None:
            logger.info("Shutting down unified backend...")
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
                self._server_process.wait()
            self._server_process = None
        self._server_url = None
    
    def is_running(self) -> bool:
        """Check if the server is currently running"""
        return self._server_url is not None


# Global instance
_auto_starter = UnifiedBackendAutoStarter()


async def ensure_unified_backend() -> str:
    """
    Ensure the unified backend is running
    Returns the base URL of the server
    """
    return await _auto_starter.ensure_running()


def shutdown_unified_backend():
    """Shutdown the auto-started backend if running"""
    _auto_starter.shutdown()


# Context manager for auto-starting backend
class AutoStartBackend:
    """Context manager that ensures backend is running"""
    
    def __init__(self):
        self.base_url = None
        
    async def __aenter__(self):
        self.base_url = await ensure_unified_backend()
        return self.base_url
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # We don't shutdown on exit - leave it running
        pass