# src/core/oauth_mixin.py

import asyncio
import json
import logging
import secrets
import webbrowser
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiohttp
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import base64
from cryptography.fernet import Fernet
import os

from .oauth_callback_server import oauth_callback_server, OAuthCallbackResult

logger = logging.getLogger(__name__)

class OAuthProvider(ABC):
    """Abstract base class for OAuth providers"""
    
    @abstractmethod
    def get_authorization_url(self, callback_url: str, state: str) -> str:
        """Get the authorization URL for the OAuth flow"""
        pass
    
    @abstractmethod
    async def exchange_code_for_tokens(self, code: str, callback_url: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token using a refresh token"""
        pass

class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 provider implementation"""
    
    def __init__(self, client_secrets_file: str, scopes: List[str]):
        self.client_secrets_file = client_secrets_file
        self.scopes = scopes
        self.flow: Optional[Flow] = None
    
    def _get_flow(self, callback_url: str) -> Flow:
        """Get configured OAuth flow"""
        if not Path(self.client_secrets_file).exists():
            raise FileNotFoundError(f"Client secrets file not found: {self.client_secrets_file}")
        
        flow = Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=self.scopes
        )
        flow.redirect_uri = callback_url
        return flow
    
    def get_authorization_url(self, callback_url: str, state: str) -> str:
        """Get Google OAuth authorization URL"""
        self.flow = self._get_flow(callback_url)
        auth_url, _ = self.flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent to get refresh token
        )
        return auth_url
    
    async def exchange_code_for_tokens(self, code: str, callback_url: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for Google tokens"""
        if not self.flow:
            self.flow = self._get_flow(callback_url)
        
        # Fetch tokens
        self.flow.fetch_token(code=code)
        
        credentials = self.flow.credentials
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Google access token"""
        # Create credentials from stored data
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.flow.client_config['client_id'] if self.flow else None,
            client_secret=self.flow.client_config['client_secret'] if self.flow else None
        )
        
        # Refresh the token
        credentials.refresh(Request())
        
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }

class TokenStorage:
    """Secure token storage with encryption"""
    
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            # Use user's home directory for credentials
            home = Path.home()
            self.storage_dir = home / ".py-mcp-bridge" / "credentials"
        else:
            self.storage_dir = Path(storage_dir)
        
        # Create directory if it doesn't exist
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # If we can't create the directory, use temp directory
            import tempfile
            self.storage_dir = Path(tempfile.gettempdir()) / "py-mcp-bridge-credentials"
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Using temporary directory for credentials: {self.storage_dir}")
        
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for token storage"""
        key_file = self.storage_dir / "encryption.key"
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def store_tokens(self, service: str, tokens: Dict[str, Any]) -> None:
        """Store encrypted tokens for a service"""
        token_file = self.storage_dir / f"{service}_tokens.enc"
        
        # Encrypt and store
        encrypted_data = self._cipher.encrypt(json.dumps(tokens).encode())
        token_file.write_bytes(encrypted_data)
        
        # Set restrictive permissions
        os.chmod(token_file, 0o600)
        logger.info(f"Stored encrypted tokens for {service}")
    
    def load_tokens(self, service: str) -> Optional[Dict[str, Any]]:
        """Load and decrypt tokens for a service"""
        token_file = self.storage_dir / f"{service}_tokens.enc"
        
        if not token_file.exists():
            return None
        
        try:
            encrypted_data = token_file.read_bytes()
            decrypted_data = self._cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt tokens for {service}: {e}")
            return None
    
    def delete_tokens(self, service: str) -> bool:
        """Delete stored tokens for a service"""
        token_file = self.storage_dir / f"{service}_tokens.enc"
        
        if token_file.exists():
            token_file.unlink()
            logger.info(f"Deleted tokens for {service}")
            return True
        return False

class OAuthMixin:
    """
    Mixin class that provides OAuth authentication capabilities to connectors.
    
    Usage:
        class MyConnector(BaseConnector, OAuthMixin):
            def __init__(self, name: str, config: Dict[str, Any]):
                super().__init__(name, config)
                self.init_oauth(
                    provider=GoogleOAuthProvider(
                        client_secrets_file="path/to/secrets.json",
                        scopes=["scope1", "scope2"]
                    )
                )
    """
    
    def init_oauth(self, provider: OAuthProvider, service_name: Optional[str] = None):
        """Initialize OAuth authentication"""
        self.oauth_provider = provider
        self.service_name = service_name or getattr(self, 'name', 'unknown')
        self.token_storage = TokenStorage()
        self._current_tokens: Optional[Dict[str, Any]] = None
    
    async def authenticate(self, force_reauth: bool = False) -> bool:
        """
        Perform OAuth authentication flow
        
        Args:
            force_reauth: Force re-authentication even if tokens exist
            
        Returns:
            True if authentication successful, False otherwise
        """
        # Check for existing valid tokens
        if not force_reauth:
            stored_tokens = self.token_storage.load_tokens(self.service_name)
            if stored_tokens:
                # Try to use existing tokens
                if await self._validate_tokens(stored_tokens):
                    self._current_tokens = stored_tokens
                    logger.info(f"Using existing tokens for {self.service_name}")
                    return True
                
                # Try to refresh if we have a refresh token
                if stored_tokens.get('refresh_token'):
                    try:
                        refreshed_tokens = await self.oauth_provider.refresh_token(
                            stored_tokens['refresh_token']
                        )
                        # Merge with existing tokens (preserve refresh_token if not returned)
                        merged_tokens = {**stored_tokens, **refreshed_tokens}
                        self.token_storage.store_tokens(self.service_name, merged_tokens)
                        self._current_tokens = merged_tokens
                        logger.info(f"Refreshed tokens for {self.service_name}")
                        return True
                    except Exception as e:
                        logger.warning(f"Token refresh failed for {self.service_name}: {e}")
        
        # Perform new OAuth flow
        return await self._perform_oauth_flow()
    
    async def _perform_oauth_flow(self) -> bool:
        """Perform the complete OAuth flow with callback server"""
        try:
            # Ensure callback server is running
            if not oauth_callback_server.server_started:
                await oauth_callback_server.start_server()
            
            # Generate state parameter for security
            state = secrets.token_urlsafe(32)
            
            # Get callback URL and authorization URL
            callback_url = oauth_callback_server.get_callback_url(self.service_name)
            auth_url = self.oauth_provider.get_authorization_url(callback_url, state)
            
            # Set up callback handler
            callback_future = asyncio.Future()
            
            async def callback_handler(result: OAuthCallbackResult):
                """Handle the OAuth callback"""
                if result.success and result.code:
                    try:
                        # Exchange code for tokens
                        tokens = await self.oauth_provider.exchange_code_for_tokens(
                            result.code, callback_url, result.state
                        )
                        
                        # Store tokens securely
                        self.token_storage.store_tokens(self.service_name, tokens)
                        self._current_tokens = tokens
                        
                        callback_future.set_result(True)
                        logger.info(f"Successfully completed OAuth flow for {self.service_name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to exchange code for tokens: {e}")
                        callback_future.set_exception(e)
                else:
                    error_msg = result.error or "OAuth callback failed"
                    logger.error(f"OAuth callback error for {self.service_name}: {error_msg}")
                    callback_future.set_exception(Exception(error_msg))
            
            # Register callback handler
            oauth_callback_server.register_callback_handler(
                self.service_name, callback_handler, state,
                connector_name=getattr(self, 'name', 'unknown')
            )
            
            # Open browser for user authorization
            logger.info(f"Opening browser for {self.service_name} authorization...")
            logger.info(f"OAuth Authentication Required for {self.service_name}")
            logger.info(f"Opening browser to: {auth_url}")
            logger.info(f"If browser doesn't open, manually visit the URL above")
            logger.info(f"Waiting for authorization (timeout: 5 minutes)...")
            
            webbrowser.open(auth_url)
            
            # Wait for callback with timeout
            try:
                result = await asyncio.wait_for(callback_future, timeout=300)  # 5 minutes
                return result
            except asyncio.TimeoutError:
                logger.error(f"OAuth flow timed out for {self.service_name}")
                return False
                
        except Exception as e:
            logger.error(f"OAuth flow failed for {self.service_name}: {e}")
            return False
    
    async def _validate_tokens(self, tokens: Dict[str, Any]) -> bool:
        """Validate if tokens are still valid"""
        # Basic validation - check if access_token exists
        if not tokens.get('access_token'):
            return False
        
        # Check expiry if available
        if tokens.get('expiry'):
            try:
                from datetime import datetime
                expiry = datetime.fromisoformat(tokens['expiry'])
                if datetime.now() >= expiry:
                    return False
            except Exception:
                # If we can't parse expiry, assume expired
                return False
        
        # Could add more provider-specific validation here
        return True
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token"""
        if self._current_tokens:
            return self._current_tokens.get('access_token')
        return None
    
    def get_credentials(self) -> Optional[Dict[str, Any]]:
        """Get all current credentials"""
        return self._current_tokens
    
    async def revoke_authentication(self) -> bool:
        """Revoke authentication and delete stored tokens"""
        try:
            # Delete stored tokens
            self.token_storage.delete_tokens(self.service_name)
            self._current_tokens = None
            logger.info(f"Revoked authentication for {self.service_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke authentication for {self.service_name}: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        return self._current_tokens is not None and self._current_tokens.get('access_token') is not None

# Convenience function for Google OAuth
def create_google_oauth_provider(client_secrets_file: str, scopes: List[str]) -> GoogleOAuthProvider:
    """Create a Google OAuth provider with the given configuration"""
    return GoogleOAuthProvider(client_secrets_file, scopes)
