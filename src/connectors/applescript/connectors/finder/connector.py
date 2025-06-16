"""
Finder AppleScript Connector

Provides comprehensive Finder file system automation through AppleScript.
"""

import logging
import subprocess
from typing import Dict, List, Any, Optional

from core.base_connector import BaseConnector
from core.models import ToolDefinition, ResourceDefinition

logger = logging.getLogger(__name__)


class FinderConnector(BaseConnector):
    """Finder file system automation connector using AppleScript."""

    def __init__(self):
        super().__init__()
        self.app_name = "Finder"

    def get_tools(self) -> List[ToolDefinition]:
        """Return the tools provided by this connector."""
        return [
            ToolDefinition(
                name="finder_open_folder",
                description="Open a folder in Finder",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to folder to open"
                        },
                        "new_window": {
                            "type": "boolean",
                            "description": "Open in new window (default: false)",
                            "default": False
                        }
                    },
                    "required": ["path"]
                }
            ),
            ToolDefinition(
                name="finder_get_selection",
                description="Get currently selected items in Finder",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="finder_select_items",
                description="Select specific items in Finder",
                input_schema={
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file/folder paths to select"
                        }
                    },
                    "required": ["paths"]
                }
            ),
            ToolDefinition(
                name="finder_move_to_trash",
                description="Move items to trash",
                input_schema={
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file/folder paths to trash"
                        }
                    },
                    "required": ["paths"]
                }
            ),
            ToolDefinition(
                name="finder_empty_trash",
                description="Empty the trash",
                input_schema={
                    "type": "object",
                    "properties": {
                        "confirm": {
                            "type": "boolean",
                            "description": "Confirmation required (default: false)",
                            "default": False
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="finder_get_info",
                description="Get information about a file or folder",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to file or folder"
                        }
                    },
                    "required": ["path"]
                }
            ),
            ToolDefinition(
                name="finder_create_folder",
                description="Create a new folder",
                input_schema={
                    "type": "object",
                    "properties": {
                        "parent_path": {
                            "type": "string",
                            "description": "Parent directory path"
                        },
                        "folder_name": {
                            "type": "string",
                            "description": "Name of new folder"
                        }
                    },
                    "required": ["parent_path", "folder_name"]
                }
            ),
            ToolDefinition(
                name="finder_duplicate_items",
                description="Duplicate files or folders",
                input_schema={
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file/folder paths to duplicate"
                        }
                    },
                    "required": ["paths"]
                }
            ),
            ToolDefinition(
                name="finder_set_view",
                description="Set Finder view mode for a window",
                input_schema={
                    "type": "object",
                    "properties": {
                        "view_mode": {
                            "type": "string",
                            "enum": ["icon", "list", "column", "cover flow"],
                            "description": "View mode to set"
                        }
                    },
                    "required": ["view_mode"]
                }
            ),
            ToolDefinition(
                name="finder_search",
                description="Search for files using Finder",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "location": {
                            "type": "string",
                            "description": "Search location (default: entire Mac)"
                        }
                    },
                    "required": ["query"]
                }
            )
        ]

    def get_resources(self) -> List[ResourceDefinition]:
        """Return the resources provided by this connector."""
        return [
            ResourceDefinition(
                uri="finder://desktop",
                name="Desktop Items",
                description="Items on the desktop",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="finder://selection",
                name="Selected Items",
                description="Currently selected items in Finder",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="finder://trash",
                name="Trash Items",
                description="Items in the trash",
                mimeType="application/json"
            )
        ]

    def _run_applescript(self, script: str) -> str:
        """Execute AppleScript and return the result."""
        try:
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
            if tool_name == "finder_open_folder":
                return self._open_folder(arguments)
            elif tool_name == "finder_get_selection":
                return self._get_selection()
            elif tool_name == "finder_select_items":
                return self._select_items(arguments)
            elif tool_name == "finder_move_to_trash":
                return self._move_to_trash(arguments)
            elif tool_name == "finder_empty_trash":
                return self._empty_trash(arguments)
            elif tool_name == "finder_get_info":
                return self._get_info(arguments)
            elif tool_name == "finder_create_folder":
                return self._create_folder(arguments)
            elif tool_name == "finder_duplicate_items":
                return self._duplicate_items(arguments)
            elif tool_name == "finder_set_view":
                return self._set_view(arguments)
            elif tool_name == "finder_search":
                return self._search(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {str(e)}")
            return {"error": str(e)}

    def _open_folder(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Open a folder in Finder."""
        path = arguments["path"]
        new_window = arguments.get("new_window", False)
        
        if new_window:
            script = f'''
            tell application "Finder"
                activate
                make new Finder window to folder (POSIX file "{path}" as alias)
            end tell
            '''
        else:
            script = f'''
            tell application "Finder"
                activate
                open folder (POSIX file "{path}" as alias)
            end tell
            '''
        
        self._run_applescript(script)
        return {"success": True, "path": path, "new_window": new_window}

    def _get_selection(self) -> Dict[str, Any]:
        """Get currently selected items in Finder."""
        script = '''
        tell application "Finder"
            set selectedItems to selection
            set itemList to {}
            
            repeat with selectedItem in selectedItems
                set itemName to name of selectedItem
                set itemPath to POSIX path of (selectedItem as alias)
                set itemKind to kind of selectedItem
                set itemInfo to itemName & "|" & itemPath & "|" & itemKind
                set end of itemList to itemInfo
            end repeat
            
            return itemList
        end tell
        '''
        
        result = self._run_applescript(script)
        
        items = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 3:
                    items.append({
                        "name": parts[0],
                        "path": parts[1],
                        "kind": parts[2]
                    })
        
        return {"selected_items": items, "total_count": len(items)}

    def _select_items(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Select specific items in Finder."""
        paths = arguments["paths"]
        
        # Build AppleScript to select multiple items
        path_references = []
        for path in paths:
            path_references.append(f'(POSIX file "{path}" as alias)')
        
        items_list = ", ".join(path_references)
        
        script = f'''
        tell application "Finder"
            activate
            select {{{items_list}}}
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "selected_paths": paths}

    def _move_to_trash(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Move items to trash."""
        paths = arguments["paths"]
        
        # Build AppleScript to trash multiple items
        path_references = []
        for path in paths:
            path_references.append(f'(POSIX file "{path}" as alias)')
        
        items_list = ", ".join(path_references)
        
        script = f'''
        tell application "Finder"
            move {{{items_list}}} to trash
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "trashed_paths": paths}

    def _empty_trash(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Empty the trash."""
        confirm = arguments.get("confirm", False)
        
        if not confirm:
            return {"error": "Empty trash requires confirmation. Set 'confirm' to true."}
        
        script = '''
        tell application "Finder"
            empty trash
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "action": "trash_emptied"}

    def _get_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about a file or folder."""
        path = arguments["path"]
        
        script = f'''
        tell application "Finder"
            set targetItem to (POSIX file "{path}" as alias)
            
            set itemName to name of targetItem
            set itemKind to kind of targetItem
            set itemSize to size of targetItem
            set itemCreated to creation date of targetItem as string
            set itemModified to modification date of targetItem as string
            
            return itemName & "|" & itemKind & "|" & itemSize & "|" & itemCreated & "|" & itemModified
        end tell
        '''
        
        result = self._run_applescript(script)
        parts = result.split("|")
        
        if len(parts) >= 5:
            return {
                "name": parts[0],
                "kind": parts[1],
                "size": int(parts[2]) if parts[2].isdigit() else parts[2],
                "created": parts[3],
                "modified": parts[4],
                "path": path
            }
        else:
            return {"error": "Could not get file information"}

    def _create_folder(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new folder."""
        parent_path = arguments["parent_path"]
        folder_name = arguments["folder_name"]
        
        script = f'''
        tell application "Finder"
            set parentFolder to folder (POSIX file "{parent_path}" as alias)
            set newFolder to make new folder at parentFolder with properties {{name:"{folder_name}"}}
            return POSIX path of (newFolder as alias)
        end tell
        '''
        
        result = self._run_applescript(script)
        return {
            "success": True,
            "folder_name": folder_name,
            "parent_path": parent_path,
            "new_folder_path": result
        }

    def _duplicate_items(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Duplicate files or folders."""
        paths = arguments["paths"]
        
        duplicated_paths = []
        for path in paths:
            script = f'''
            tell application "Finder"
                set originalItem to (POSIX file "{path}" as alias)
                set duplicatedItem to duplicate originalItem
                return POSIX path of (duplicatedItem as alias)
            end tell
            '''
            
            result = self._run_applescript(script)
            duplicated_paths.append(result)
        
        return {
            "success": True,
            "original_paths": paths,
            "duplicated_paths": duplicated_paths
        }

    def _set_view(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Set Finder view mode for a window."""
        view_mode = arguments["view_mode"]
        
        view_mapping = {
            "icon": "icon view",
            "list": "list view",
            "column": "column view",
            "cover flow": "flow view"
        }
        
        finder_view = view_mapping.get(view_mode, "icon view")
        
        script = f'''
        tell application "Finder"
            set current view of front window to {finder_view}
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "view_mode": view_mode}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for files using Finder."""
        query = arguments["query"]
        location = arguments.get("location", "")
        
        script = f'''
        tell application "Finder"
            activate
            
            if "{location}" is not "" then
                set searchLocation to folder (POSIX file "{location}" as alias)
                set searchResults to search searchLocation for "{query}"
            else
                set searchResults to search for "{query}"
            end if
            
            return "search_initiated"
        end tell
        '''
        
        result = self._run_applescript(script)
        return {
            "success": True,
            "query": query,
            "location": location or "entire Mac",
            "status": result
        }

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI."""
        try:
            if uri == "finder://desktop":
                script = '''
                tell application "Finder"
                    set desktopItems to items of desktop
                    set itemList to {}
                    
                    repeat with desktopItem in desktopItems
                        set itemName to name of desktopItem
                        set itemKind to kind of desktopItem
                        set itemInfo to itemName & "|" & itemKind
                        set end of itemList to itemInfo
                    end repeat
                    
                    return itemList
                end tell
                '''
                
                result = self._run_applescript(script)
                items = []
                if result and result != "{}":
                    lines = result.split(", ")
                    for line in lines:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            items.append({
                                "name": parts[0],
                                "kind": parts[1]
                            })
                
                return {"desktop_items": items}
                
            elif uri == "finder://selection":
                return self._get_selection()
                
            elif uri == "finder://trash":
                script = '''
                tell application "Finder"
                    set trashItems to items of trash
                    set itemList to {}
                    
                    repeat with trashItem in trashItems
                        set itemName to name of trashItem
                        set itemKind to kind of trashItem
                        set itemInfo to itemName & "|" & itemKind
                        set end of itemList to itemInfo
                    end repeat
                    
                    return itemList
                end tell
                '''
                
                result = self._run_applescript(script)
                items = []
                if result and result != "{}":
                    lines = result.split(", ")
                    for line in lines:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            items.append({
                                "name": parts[0],
                                "kind": parts[1]
                            })
                
                return {"trash_items": items}
                
            else:
                return {"error": f"Unknown resource URI: {uri}"}
                
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {str(e)}")
            return {"error": str(e)}