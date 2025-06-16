"""
OAuth Integration for Unified Backend
Replaces the standalone OAuth callback server with unified backend integration
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class UnifiedOAuthManager:
    """
    Manages OAuth flows through the unified backend server
    """
    
    def __init__(self, unified_server):
        self.server = unified_server
        self.callback_handlers: Dict[str, Callable] = {}
        self.pending_authorizations: Dict[str, Dict[str, Any]] = {}
        
    def get_callback_url(self, service: Optional[str] = None) -> str:
        """Get the OAuth callback URL for a service"""
        if service:
            return f"{self.server.base_url}/oauth/{service}/callback"
        return f"{self.server.base_url}/oauth/callback"
    
    def get_base_url(self) -> str:
        """Get the base URL of the unified server"""
        return self.server.base_url
    
    async def register_authorization(self, service: str, state: str, 
                                   callback: Optional[Callable] = None) -> str:
        """Register an OAuth authorization attempt"""
        auth_id = str(uuid.uuid4())
        
        self.pending_authorizations[state] = {
            'id': auth_id,
            'service': service,
            'state': state,
            'callback': callback,
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        logger.info(f"Registered OAuth authorization for {service} with state {state}")
        return auth_id
    
    async def wait_for_callback(self, state: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for an OAuth callback with the given state"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            # Check pending OAuth callbacks in the server
            callbacks = self.server.get_pending_oauth_callbacks()
            
            for callback in callbacks:
                if callback.get('state') == state:
                    # Found our callback
                    auth_info = self.pending_authorizations.pop(state, {})
                    
                    # Process callback
                    result = {
                        'success': callback.get('code') is not None,
                        'code': callback.get('code'),
                        'state': callback.get('state'),
                        'error': callback.get('error'),
                        'service': callback.get('service'),
                        'auth_info': auth_info
                    }
                    
                    # Remove from server
                    self.server.get_oauth_callback(callback['id'])
                    
                    # Call registered callback if any
                    if auth_info.get('callback'):
                        try:
                            await auth_info['callback'](result)
                        except Exception as e:
                            logger.error(f"Error in OAuth callback handler: {e}")
                    
                    return result
            
            # Wait a bit before checking again
            await asyncio.sleep(0.5)
        
        # Timeout
        auth_info = self.pending_authorizations.pop(state, {})
        return {
            'success': False,
            'error': 'timeout',
            'error_description': f'OAuth callback not received within {timeout} seconds',
            'state': state,
            'auth_info': auth_info
        }
    
    def register_service_handler(self, service: str, handler: Callable):
        """Register a custom OAuth handler for a specific service"""
        self.server.register_oauth_handler(service, handler)
        logger.info(f"Registered custom OAuth handler for {service}")


# Global instance that will be initialized with the server
_oauth_manager: Optional[UnifiedOAuthManager] = None


def get_oauth_manager() -> UnifiedOAuthManager:
    """Get the global OAuth manager instance"""
    if _oauth_manager is None:
        raise RuntimeError("OAuth manager not initialized. Start the unified server first.")
    return _oauth_manager


def initialize_oauth_manager(unified_server) -> UnifiedOAuthManager:
    """Initialize the global OAuth manager with a unified server instance"""
    global _oauth_manager
    _oauth_manager = UnifiedOAuthManager(unified_server)
    return _oauth_manager


# Compatibility layer for existing code
class OAuthCallbackServerCompat:
    """
    Compatibility layer to make the unified backend work with existing OAuth code
    """
    
    def __init__(self):
        self._manager = None
        
    async def start_server(self) -> str:
        """Start server (no-op, unified server handles this)"""
        manager = get_oauth_manager()
        return manager.get_base_url()
    
    async def stop_server(self):
        """Stop server (no-op, unified server handles this)"""
        pass
    
    def get_callback_url(self, path: str = "/callback") -> str:
        """Get callback URL"""
        manager = get_oauth_manager()
        if path.startswith('/'):
            path = path[1:]
        return f"{manager.get_base_url()}/{path}"
    
    async def wait_for_callback(self, state: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for OAuth callback"""
        manager = get_oauth_manager()
        return await manager.wait_for_callback(state, timeout)
    
    def register_state_handler(self, state: str, handler: Callable):
        """Register a state handler"""
        manager = get_oauth_manager()
        asyncio.create_task(
            manager.register_authorization('unknown', state, handler)
        )


# Create compatibility instance
oauth_callback_server = OAuthCallbackServerCompat()