"""
Shared Google OAuth service for all Google connectors
Handles authentication once for Gmail, Calendar, Tasks, Drive, etc.
"""

import os
import pickle
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    """Centralized Google OAuth management for all Google services"""
    
    # Shared instance
    _instance = None
    _lock = asyncio.Lock()
    
    # All Google scopes needed by any connector
    ALL_SCOPES = [
        # Gmail
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
        # Calendar
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events',
        # Tasks
        'https://www.googleapis.com/auth/tasks',
        # Drive
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata.readonly',
    ]
    
    def __init__(self):
        self.credentials = None
        self.services = {}
        self._auth_in_progress = False
        self._monitor_task = None
        
        # Paths - dynamically determine project root
        project_root = Path(__file__).parent.parent.parent
        self.base_dir = project_root / "credentials"
        self.credentials_file = self.base_dir / "google_credentials.json"
        self.token_file = self.base_dir / "google_token.pickle"
        self.state_file = self.base_dir / "google_oauth_state.json"
        
    @classmethod
    async def get_instance(cls) -> "GoogleOAuthService":
        """Get or create the shared instance"""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                await cls._instance.initialize()
            return cls._instance
    
    async def initialize(self):
        """Initialize the OAuth service"""
        try:
            await self._load_or_refresh_credentials()
            
            if not self.credentials:
                # Start monitoring for credentials
                if not self.credentials_file.exists():
                    await self._create_setup_guide()
                    self._monitor_task = asyncio.create_task(self._monitor_for_credentials())
                else:
                    # Credentials file exists, start OAuth flow
                    await self._run_oauth_flow()
                    
        except Exception as e:
            logger.error(f"Failed to initialize Google OAuth: {e}")
    
    async def _load_or_refresh_credentials(self) -> bool:
        """Load existing credentials or refresh if needed"""
        if self.token_file.exists():
            try:
                with open(str(self.token_file), 'rb') as token:
                    self.credentials = pickle.load(token)
                    
                # Check if token needs refresh
                if self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    
                if self.credentials.valid:
                    logger.debug("Google OAuth credentials loaded successfully")
                    return True
                    
            except Exception as e:
                logger.warning(f"Failed to load/refresh token: {e}")
                self.credentials = None
                
        return False
    
    async def _create_setup_guide(self):
        """Create setup guide when credentials are missing"""
        guide_path = self.credentials_file.with_name(self.credentials_file.stem + '_SETUP_GUIDE.txt')
        
        guide_content = f"""
GOOGLE OAUTH SETUP REQUIRED
===========================

All Google services (Gmail, Calendar, Tasks, Drive) need OAuth credentials.

AUTOMATIC SETUP STEPS:
1. Visit: https://console.cloud.google.com/apis/credentials
2. Create a new project called "MCP Bridge"
3. Enable these APIs:
   - Gmail API
   - Google Calendar API
   - Google Tasks API
   - Google Drive API
4. Create OAuth 2.0 Client ID (Desktop application)
5. Download the credentials JSON
6. Save it as: {str(self.credentials_file)}

Once the file is in place, ALL Google services will automatically:
- Open your browser for one-time authorization
- Share the same authentication
- Work seamlessly together

You only need to authorize ONCE for all Google services!
"""
        
        guide_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(guide_path), 'w') as f:
            f.write(guide_content)
        
        logger.debug(f"Created Google OAuth setup guide at: {guide_path}")
        logger.debug("Waiting for Google Cloud credentials file...")
    
    async def _monitor_for_credentials(self):
        """Monitor for credentials file"""
        check_interval = 5
        max_checks = 720  # 1 hour
        
        for i in range(max_checks):
            if self.credentials_file.exists():
                logger.debug("Google credentials file detected! Starting OAuth flow...")
                await asyncio.sleep(1)
                
                try:
                    await self._run_oauth_flow()
                    return
                except Exception as e:
                    logger.error(f"OAuth flow failed: {e}")
                    return
            
            await asyncio.sleep(check_interval)
        
        logger.debug("Stopped monitoring for credentials after 1 hour")
    
    async def _run_oauth_flow(self):
        """Run the OAuth flow"""
        if self._auth_in_progress:
            logger.info("OAuth flow already in progress")
            return
            
        self._auth_in_progress = True
        
        try:
            flow = Flow.from_client_secrets_file(
                str(self.credentials_file),
                scopes=self.ALL_SCOPES
            )
            flow.redirect_uri = 'http://localhost:8080'
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            # Check environment - in MCP Bridge, stdin is always a pipe
            import sys
            if not sys.stdin.isatty():
                # MCP mode - background auth
                await self._background_oauth_flow(flow, auth_url)
            else:
                # Interactive mode
                await self._interactive_oauth_flow(flow, auth_url)
                
        except Exception as e:
            logger.error(f"OAuth flow error: {e}")
        finally:
            self._auth_in_progress = False
    
    async def _interactive_oauth_flow(self, flow, auth_url):
        """Interactive OAuth flow with browser"""
        logger.debug("Opening browser for Google authorization...")
        
        import webbrowser
        webbrowser.open(auth_url)
        
        # Import here to avoid circular dependency
        from .oauth_callback_server import run_oauth_callback_server
        
        logger.debug("Waiting for authorization (5 minute timeout)...")
        auth_code = await run_oauth_callback_server(port=8080, timeout=300)
        
        if auth_code:
            flow.fetch_token(code=auth_code)
            self.credentials = flow.credentials
            self._save_credentials()
            logger.debug("Google OAuth completed successfully!")
            logger.debug("All Google services are now authorized!")
        else:
            logger.warning("❌ OAuth authorization timed out or was cancelled")
    
    async def _background_oauth_flow(self, flow, auth_url):
        """Background OAuth for MCP mode"""
        state_data = {
            'status': 'pending',
            'auth_url': auth_url,
            'created_at': datetime.now().isoformat(),
            'services': ['Gmail', 'Calendar', 'Tasks', 'Drive'],
            'instructions': f'Visit this URL to authorize ALL Google services: {auth_url}'
        }
        
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self.state_file), 'w') as f:
            json.dump(state_data, f, indent=2)
        
        # Start background listener
        asyncio.create_task(self._oauth_background_listener(flow))
        
        logger.debug(f"Google OAuth URL: {auth_url}")
        logger.debug("Waiting for authorization (authorizes ALL Google services)...")
    
    async def _oauth_background_listener(self, flow):
        """Listen for OAuth callback in background"""
        try:
            from .oauth_callback_server import run_oauth_callback_server
            
            auth_code = await run_oauth_callback_server(port=8080, timeout=600)
            
            if auth_code:
                flow.fetch_token(code=auth_code)
                self.credentials = flow.credentials
                self._save_credentials()
                
                # Update state
                state_data = {
                    'status': 'completed',
                    'completed_at': datetime.now().isoformat(),
                    'services': ['Gmail', 'Calendar', 'Tasks', 'Drive']
                }
                with open(str(self.state_file), 'w') as f:
                    json.dump(state_data, f, indent=2)
                
                logger.debug("Google OAuth completed in background!")
                logger.debug("All Google services are now authorized!")
                
                # Clean up after delay
                await asyncio.sleep(5)
                if self.state_file.exists():
                    self.state_file.unlink()
            else:
                # Timeout
                state_data = {
                    'status': 'timeout',
                    'error': 'Authorization timeout after 10 minutes'
                }
                with open(str(self.state_file), 'w') as f:
                    json.dump(state_data, f, indent=2)
                    
        except Exception as e:
            logger.error(f"Background OAuth listener error: {e}")
    
    def _save_credentials(self):
        """Save credentials to file"""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(str(self.token_file), 'wb') as token:
            pickle.dump(self.credentials, token)
    
    async def get_service(self, service_name: str, version: str = 'v1'):
        """Get or create a Google API service"""
        if not self.credentials or not self.credentials.valid:
            # Try to refresh
            await self._load_or_refresh_credentials()
            
        if not self.credentials or not self.credentials.valid:
            return None
            
        # Cache services
        key = f"{service_name}_{version}"
        if key not in self.services:
            try:
                self.services[key] = build(service_name, version, credentials=self.credentials)
                logger.debug(f"Created {service_name} service")
            except Exception as e:
                logger.error(f"Failed to create {service_name} service: {e}")
                return None
                
        return self.services[key]
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status"""
        status = {
            'authenticated': False,
            'services_available': [],
            'credentials_file_exists': self.credentials_file.exists(),
            'token_file_exists': self.token_file.exists(),
            'auth_in_progress': self._auth_in_progress
        }
        
        if self.credentials and self.credentials.valid:
            status['authenticated'] = True
            status['services_available'] = ['gmail', 'calendar', 'tasks', 'drive']
            
        # Check for pending auth
        if self.state_file.exists():
            try:
                with open(str(self.state_file), 'r') as f:
                    state = json.load(f)
                status['auth_state'] = state.get('status')
                status['auth_url'] = state.get('auth_url')
            except:
                pass
                
        return status
    
    async def ensure_authenticated(self) -> bool:
        """Ensure authentication is complete"""
        if self.credentials and self.credentials.valid:
            return True
            
        # Try to load/refresh
        if await self._load_or_refresh_credentials():
            return True
            
        # Check if auth is pending
        if self.state_file.exists():
            try:
                with open(str(self.state_file), 'r') as f:
                    state = json.load(f)
                    
                if state.get('status') == 'completed':
                    # Try to reload credentials
                    await self._load_or_refresh_credentials()
                    return self.credentials and self.credentials.valid
            except:
                pass
                
        return False