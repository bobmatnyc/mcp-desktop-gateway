"""
Safari AppleScript Connector

Provides comprehensive Safari web browser automation through AppleScript.
"""

import logging
import subprocess
from typing import Dict, List, Any, Optional

from core.base_connector import BaseConnector
from core.models import ToolDefinition, ResourceDefinition

logger = logging.getLogger(__name__)


class SafariConnector(BaseConnector):
    """Safari browser automation connector using AppleScript."""

    def __init__(self):
        super().__init__()
        self.app_name = "Safari"

    def get_tools(self) -> List[ToolDefinition]:
        """Return the tools provided by this connector."""
        return [
            ToolDefinition(
                name="safari_open_url",
                description="Open a URL in Safari",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to open"
                        },
                        "new_tab": {
                            "type": "boolean",
                            "description": "Open in new tab (default: true)",
                            "default": True
                        },
                        "new_window": {
                            "type": "boolean",
                            "description": "Open in new window (default: false)",
                            "default": False
                        }
                    },
                    "required": ["url"]
                }
            ),
            ToolDefinition(
                name="safari_get_current_url",
                description="Get the URL of the current Safari tab",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_get_page_title",
                description="Get the title of the current Safari page",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_get_tabs",
                description="Get list of all open Safari tabs",
                input_schema={
                    "type": "object",
                    "properties": {
                        "include_content": {
                            "type": "boolean",
                            "description": "Include page content in results (default: false)",
                            "default": False
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_close_tab",
                description="Close a Safari tab",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tab_index": {
                            "type": "integer",
                            "description": "Tab index (1-based) to close. If not provided, closes current tab"
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_switch_tab",
                description="Switch to a specific Safari tab",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tab_index": {
                            "type": "integer",
                            "description": "Tab index (1-based) to switch to"
                        }
                    },
                    "required": ["tab_index"]
                }
            ),
            ToolDefinition(
                name="safari_reload_page",
                description="Reload the current Safari page",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_go_back",
                description="Go back in Safari history",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_go_forward",
                description="Go forward in Safari history",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_search",
                description="Perform a search using Safari's search bar",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "search_engine": {
                            "type": "string",
                            "description": "Search engine to use (google, bing, duckduckgo, etc.)",
                            "default": "google"
                        }
                    },
                    "required": ["query"]
                }
            ),
            ToolDefinition(
                name="safari_execute_javascript",
                description="Execute JavaScript in the current Safari tab",
                input_schema={
                    "type": "object",
                    "properties": {
                        "javascript": {
                            "type": "string",
                            "description": "JavaScript code to execute"
                        }
                    },
                    "required": ["javascript"]
                }
            ),
            ToolDefinition(
                name="safari_get_page_source",
                description="Get the HTML source of the current page",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_take_screenshot",
                description="Take a screenshot of the current Safari page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "output_path": {
                            "type": "string",
                            "description": "Path to save screenshot (default: ~/Desktop/safari_screenshot.png)"
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="safari_set_zoom",
                description="Set zoom level for current Safari page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "zoom_level": {
                            "type": "number",
                            "description": "Zoom level (1.0 = 100%, 1.5 = 150%, etc.)",
                            "minimum": 0.5,
                            "maximum": 3.0
                        }
                    },
                    "required": ["zoom_level"]
                }
            ),
            ToolDefinition(
                name="safari_add_bookmark",
                description="Add current page to Safari bookmarks",
                input_schema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Bookmark title (uses page title if not provided)"
                        },
                        "folder": {
                            "type": "string",
                            "description": "Bookmark folder name (default: Bookmarks Menu)"
                        }
                    },
                    "required": []
                }
            )
        ]

    def get_resources(self) -> List[ResourceDefinition]:
        """Return the resources provided by this connector."""
        return [
            ResourceDefinition(
                uri="safari://tabs",
                name="Safari Tabs",
                description="List of all open Safari tabs",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="safari://current",
                name="Current Safari Tab",
                description="Information about the current Safari tab",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="safari://bookmarks",
                name="Safari Bookmarks",
                description="Safari bookmark folders and items",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="safari://history",
                name="Safari History",
                description="Recent Safari browsing history",
                mimeType="application/json"
            )
        ]

    def _run_applescript(self, script: str) -> str:
        """Execute AppleScript and return the result."""
        try:
            # Check if Safari is running
            check_script = '''
            tell application "System Events"
                return (name of processes) contains "Safari"
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", check_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout.strip() == "false":
                # Launch Safari if not running
                launch_script = '''
                tell application "Safari"
                    activate
                    delay 2
                end tell
                '''
                subprocess.run(["osascript", "-e", launch_script], timeout=10)
            
            # Execute the main script
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"AppleScript error: {result.stderr}")
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            raise Exception("AppleScript execution timed out")
        except Exception as e:
            raise Exception(f"Failed to execute AppleScript: {str(e)}")

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with the given arguments."""
        try:
            if tool_name == "safari_open_url":
                return self._open_url(arguments)
            elif tool_name == "safari_get_current_url":
                return self._get_current_url()
            elif tool_name == "safari_get_page_title":
                return self._get_page_title()
            elif tool_name == "safari_get_tabs":
                return self._get_tabs(arguments)
            elif tool_name == "safari_close_tab":
                return self._close_tab(arguments)
            elif tool_name == "safari_switch_tab":
                return self._switch_tab(arguments)
            elif tool_name == "safari_reload_page":
                return self._reload_page()
            elif tool_name == "safari_go_back":
                return self._go_back()
            elif tool_name == "safari_go_forward":
                return self._go_forward()
            elif tool_name == "safari_search":
                return self._search(arguments)
            elif tool_name == "safari_execute_javascript":
                return self._execute_javascript(arguments)
            elif tool_name == "safari_get_page_source":
                return self._get_page_source()
            elif tool_name == "safari_take_screenshot":
                return self._take_screenshot(arguments)
            elif tool_name == "safari_set_zoom":
                return self._set_zoom(arguments)
            elif tool_name == "safari_add_bookmark":
                return self._add_bookmark(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {str(e)}")
            return {"error": str(e)}

    def _open_url(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Open a URL in Safari."""
        url = arguments["url"]
        new_tab = arguments.get("new_tab", True)
        new_window = arguments.get("new_window", False)
        
        if new_window:
            script = f'''
            tell application "Safari"
                activate
                make new document with properties {{URL:"{url}"}}
            end tell
            '''
        elif new_tab:
            script = f'''
            tell application "Safari"
                activate
                tell front window
                    make new tab with properties {{URL:"{url}"}}
                    set current tab to last tab
                end tell
            end tell
            '''
        else:
            script = f'''
            tell application "Safari"
                activate
                set URL of front document to "{url}"
            end tell
            '''
        
        self._run_applescript(script)
        return {"success": True, "url": url, "action": "opened"}

    def _get_current_url(self) -> Dict[str, Any]:
        """Get the URL of the current Safari tab."""
        script = '''
        tell application "Safari"
            return URL of front document
        end tell
        '''
        
        url = self._run_applescript(script)
        return {"url": url}

    def _get_page_title(self) -> Dict[str, Any]:
        """Get the title of the current Safari page."""
        script = '''
        tell application "Safari"
            return name of front document
        end tell
        '''
        
        title = self._run_applescript(script)
        return {"title": title}

    def _get_tabs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of all open Safari tabs."""
        include_content = arguments.get("include_content", False)
        
        if include_content:
            script = '''
            tell application "Safari"
                set tabList to {}
                repeat with w from 1 to (count of windows)
                    repeat with t from 1 to (count of tabs of window w)
                        set tabInfo to {URL:(URL of tab t of window w), title:(name of tab t of window w), window:w, tab:t}
                        set end of tabList to tabInfo
                    end repeat
                end repeat
                return tabList
            end tell
            '''
        else:
            script = '''
            tell application "Safari"
                set tabList to {}
                repeat with w from 1 to (count of windows)
                    repeat with t from 1 to (count of tabs of window w)
                        set tabInfo to (URL of tab t of window w) & " | " & (name of tab t of window w)
                        set end of tabList to tabInfo
                    end repeat
                end repeat
                return tabList
            end tell
            '''
        
        result = self._run_applescript(script)
        
        # Parse the result into a more structured format
        tabs = []
        if result:
            lines = result.split(", ")
            for i, line in enumerate(lines):
                if " | " in line:
                    url, title = line.split(" | ", 1)
                    tabs.append({
                        "index": i + 1,
                        "url": url.strip(),
                        "title": title.strip()
                    })
        
        return {"tabs": tabs, "total_count": len(tabs)}

    def _close_tab(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Close a Safari tab."""
        tab_index = arguments.get("tab_index")
        
        if tab_index:
            script = f'''
            tell application "Safari"
                close tab {tab_index} of front window
            end tell
            '''
        else:
            script = '''
            tell application "Safari"
                close current tab of front window
            end tell
            '''
        
        self._run_applescript(script)
        return {"success": True, "action": "tab_closed"}

    def _switch_tab(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to a specific Safari tab."""
        tab_index = arguments["tab_index"]
        
        script = f'''
        tell application "Safari"
            set current tab of front window to tab {tab_index} of front window
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "current_tab": tab_index}

    def _reload_page(self) -> Dict[str, Any]:
        """Reload the current Safari page."""
        script = '''
        tell application "Safari"
            tell front document to reload
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "action": "page_reloaded"}

    def _go_back(self) -> Dict[str, Any]:
        """Go back in Safari history."""
        script = '''
        tell application "Safari"
            tell front document to go back
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "action": "went_back"}

    def _go_forward(self) -> Dict[str, Any]:
        """Go forward in Safari history."""
        script = '''
        tell application "Safari"
            tell front document to go forward
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "action": "went_forward"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a search using Safari."""
        query = arguments["query"]
        search_engine = arguments.get("search_engine", "google")
        
        # Map search engines to URLs
        search_urls = {
            "google": f"https://www.google.com/search?q={query}",
            "bing": f"https://www.bing.com/search?q={query}",
            "duckduckgo": f"https://duckduckgo.com/?q={query}",
            "yahoo": f"https://search.yahoo.com/search?p={query}"
        }
        
        search_url = search_urls.get(search_engine, search_urls["google"])
        
        # URL encode the query properly
        import urllib.parse
        encoded_query = urllib.parse.quote_plus(query)
        search_url = search_url.replace(query, encoded_query)
        
        script = f'''
        tell application "Safari"
            activate
            set URL of front document to "{search_url}"
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "query": query, "search_engine": search_engine, "url": search_url}

    def _execute_javascript(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute JavaScript in the current Safari tab."""
        javascript = arguments["javascript"]
        
        # Escape quotes in JavaScript
        escaped_js = javascript.replace('"', '\\"').replace("'", "\\'")
        
        script = f'''
        tell application "Safari"
            return do JavaScript "{escaped_js}" in front document
        end tell
        '''
        
        result = self._run_applescript(script)
        return {"success": True, "result": result}

    def _get_page_source(self) -> Dict[str, Any]:
        """Get the HTML source of the current page."""
        script = '''
        tell application "Safari"
            return do JavaScript "document.documentElement.outerHTML" in front document
        end tell
        '''
        
        source = self._run_applescript(script)
        return {"source": source}

    def _take_screenshot(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Take a screenshot of the current Safari page."""
        output_path = arguments.get("output_path", "~/Desktop/safari_screenshot.png")
        
        script = f'''
        tell application "Safari"
            activate
        end tell
        
        delay 1
        
        tell application "System Events"
            keystroke "4" using {{command down, shift down}}
            delay 2
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "screenshot_path": output_path}

    def _set_zoom(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Set zoom level for current Safari page."""
        zoom_level = arguments["zoom_level"]
        
        # Convert zoom level to percentage
        zoom_percent = int(zoom_level * 100)
        
        script = f'''
        tell application "Safari"
            tell front document
                set text size to {zoom_percent}
            end tell
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "zoom_level": zoom_level}

    def _add_bookmark(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add current page to Safari bookmarks."""
        title = arguments.get("title")
        folder = arguments.get("folder", "Bookmarks Menu")
        
        if title:
            script = f'''
            tell application "Safari"
                add front document to bookmarks with name "{title}"
            end tell
            '''
        else:
            script = '''
            tell application "Safari"
                add front document to bookmarks
            end tell
            '''
        
        self._run_applescript(script)
        return {"success": True, "action": "bookmark_added"}

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI."""
        try:
            if uri == "safari://tabs":
                return self._get_tabs({"include_content": True})
            elif uri == "safari://current":
                url_result = self._get_current_url()
                title_result = self._get_page_title()
                return {
                    "url": url_result.get("url"),
                    "title": title_result.get("title")
                }
            elif uri == "safari://bookmarks":
                # This would require more complex AppleScript to read bookmarks
                return {"message": "Bookmark reading not yet implemented"}
            elif uri == "safari://history":
                # This would require accessing Safari's history database
                return {"message": "History reading not yet implemented"}
            else:
                return {"error": f"Unknown resource URI: {uri}"}
                
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {str(e)}")
            return {"error": str(e)}