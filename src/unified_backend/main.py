#!/usr/bin/env python3
"""
Main entry point for MCP Bridge with Unified Backend
Consolidates all HTTP services into a single server
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from src.unified_backend.server import UnifiedServer
from src.unified_backend.oauth_integration import initialize_oauth_manager
from src.core.registry import ConnectorRegistry
from src.core.config import ConfigManager
from src.mcp_server import ModularMCPServer

logger = logging.getLogger(__name__)


class UnifiedMCPBridge:
    """
    Main application class that runs both the unified backend and MCP server
    """
    
    def __init__(self):
        self.unified_server: Optional[UnifiedServer] = None
        self.mcp_server: Optional[ModularMCPServer] = None
        self.registry = ConnectorRegistry()
        self.config_manager = ConfigManager()
        self._shutdown_event = asyncio.Event()
        
    async def start_unified_backend(self) -> str:
        """Start the unified backend server"""
        self.unified_server = UnifiedServer(port_range=(3000, 3003))
        base_url = await self.unified_server.start()
        
        # Initialize OAuth manager with the server
        initialize_oauth_manager(self.unified_server)
        
        logger.info(f"Unified backend started at {base_url}")
        return base_url
    
    async def initialize_connectors(self):
        """Initialize all enabled connectors"""
        try:
            # Auto-discover connectors
            self.registry.auto_discover_connectors()
            
            # Get enabled connectors from config
            enabled_connectors = self.config_manager.get_enabled_connectors()
            
            logger.info(f"Initializing {len(enabled_connectors)} enabled connectors...")
            
            for connector_name in enabled_connectors:
                try:
                    connector_config = self.config_manager.get_connector_config(connector_name)
                    # Extract the config dict from the ConnectorConfig object
                    config_dict = connector_config.config if hasattr(connector_config, 'config') else connector_config
                    await self.registry.initialize_connector(connector_name, config_dict)
                    logger.info(f"✅ Initialized connector: {connector_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to initialize connector {connector_config}: {e}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Failed to initialize connectors: {e}")
            raise
    
    async def start_mcp_server(self):
        """Start the MCP server for Claude Desktop"""
        self.mcp_server = ModularMCPServer()
        
        # Share the same registry
        self.mcp_server.registry = self.registry
        
        # Run MCP server in background
        asyncio.create_task(self.mcp_server.start())
        logger.info("MCP server started")
    
    async def run(self):
        """Run the complete unified MCP Bridge"""
        try:
            # Start unified backend first
            base_url = await self.start_unified_backend()
            
            if sys.stdout.isatty():
                print(f"\n🚀 MCP Bridge Unified Backend Started!")
                print(f"📍 Base URL: {base_url}")
                print(f"🔌 Port: {self.unified_server.port}")
                print(f"\nServices:")
                print(f"  🔐 OAuth: {base_url}/oauth/callback")
                print(f"  🌐 Extension API: {base_url}/api/extension/")
                print(f"  📡 WebSocket: ws://localhost:{self.unified_server.port}/ws")
                print(f"  🏥 Health: {base_url}/health")
                print(f"  🐛 Debug: {base_url}/debug")
                
            # Initialize connectors
            await self.initialize_connectors()
            
            # Start MCP server
            await self.start_mcp_server()
            
            if sys.stdout.isatty():
                print(f"\n✅ MCP Bridge Ready!")
                print(f"📱 Claude Desktop can now connect")
                print(f"🔧 All services consolidated on port {self.unified_server.port}")
                print(f"\n⏹️  Press Ctrl+C to stop\n")
            
            # Wait for shutdown
            await self._shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Starting graceful shutdown...")
        
        # Stop MCP server
        if self.mcp_server:
            # MCP server handles its own shutdown
            pass
        
        # Shutdown connectors
        await self.registry.shutdown_all()
        
        # Stop unified backend
        if self.unified_server:
            await self.unified_server.stop()
        
        logger.info("Graceful shutdown completed")
    
    def request_shutdown(self):
        """Request application shutdown"""
        self._shutdown_event.set()


def setup_signal_handlers(app: UnifiedMCPBridge):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        app.request_shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def run_unified_mode():
    """Run in unified mode with consolidated backend"""
    app = UnifiedMCPBridge()
    setup_signal_handlers(app)
    await app.run()


async def run_backend_only():
    """Run only the unified backend server (for development)"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    server = UnifiedServer()
    base_url = await server.start()
    
    print(f"\n🚀 Unified Backend Server Started!")
    print(f"📍 Base URL: {base_url}")
    print(f"🔌 Port: {server.port}")
    print(f"\nEndpoints:")
    print(f"  Health: {base_url}/health")
    print(f"  Debug: {base_url}/debug")
    print(f"  OAuth: {base_url}/oauth/callback")
    print(f"  Extension API: {base_url}/api/extension/")
    print(f"  WebSocket: ws://localhost:{server.port}/ws")
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await server.stop()


def main():
    """Main entry point with mode selection"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Bridge with Unified Backend")
    parser.add_argument(
        "--mode",
        choices=["unified", "mcp", "backend"],
        default="unified",
        help="Run mode: 'unified' (full system), 'mcp' (MCP only), 'backend' (backend only)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr) if not sys.stdout.isatty()
            else logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress verbose libraries
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Run based on mode
    if args.mode == "unified":
        asyncio.run(run_unified_mode())
    elif args.mode == "backend":
        asyncio.run(run_backend_only())
    elif args.mode == "mcp":
        # Legacy MCP-only mode
        from src.main import run_mcp_mode
        asyncio.run(run_mcp_mode())


if __name__ == "__main__":
    main()