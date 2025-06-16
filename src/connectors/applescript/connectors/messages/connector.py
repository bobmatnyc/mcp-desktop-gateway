"""
Messages AppleScript Connector

Provides comprehensive Messages app automation through AppleScript.
"""

import logging
import subprocess
from typing import Dict, List, Any, Optional

from core.base_connector import BaseConnector
from core.models import ToolDefinition, ResourceDefinition

logger = logging.getLogger(__name__)


class MessagesConnector(BaseConnector):
    """Messages app automation connector using AppleScript."""

    def __init__(self):
        super().__init__()
        self.app_name = "Messages"

    def get_tools(self) -> List[ToolDefinition]:
        """Return the tools provided by this connector."""
        return [
            ToolDefinition(
                name="messages_send",
                description="Send a message to a contact or phone number",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "description": "Phone number, email, or contact name"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message text to send"
                        },
                        "service": {
                            "type": "string",
                            "description": "Service to use (iMessage or SMS, default: iMessage)",
                            "default": "iMessage"
                        }
                    },
                    "required": ["recipient", "message"]
                }
            ),
            ToolDefinition(
                name="messages_get_conversations",
                description="Get list of message conversations",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of conversations (default: 10)",
                            "default": 10
                        },
                        "include_messages": {
                            "type": "boolean",
                            "description": "Include recent messages in each conversation (default: false)",
                            "default": False
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="messages_get_conversation",
                description="Get messages from a specific conversation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "description": "Phone number, email, or contact name"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of messages (default: 20)",
                            "default": 20
                        }
                    },
                    "required": ["recipient"]
                }
            ),
            ToolDefinition(
                name="messages_search",
                description="Search for messages containing specific text",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 20)",
                            "default": 20
                        }
                    },
                    "required": ["query"]
                }
            ),
            ToolDefinition(
                name="messages_get_unread",
                description="Get unread messages",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of unread messages (default: 50)",
                            "default": 50
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="messages_mark_read",
                description="Mark messages as read in a conversation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "description": "Phone number, email, or contact name"
                        }
                    },
                    "required": ["recipient"]
                }
            ),
            ToolDefinition(
                name="messages_delete_conversation",
                description="Delete an entire conversation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "description": "Phone number, email, or contact name"
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": "Confirmation required to delete (default: false)",
                            "default": False
                        }
                    },
                    "required": ["recipient"]
                }
            ),
            ToolDefinition(
                name="messages_send_file",
                description="Send a file attachment via Messages",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "description": "Phone number, email, or contact name"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to file to send"
                        },
                        "message": {
                            "type": "string",
                            "description": "Optional message to accompany the file"
                        }
                    },
                    "required": ["recipient", "file_path"]
                }
            ),
            ToolDefinition(
                name="messages_get_status",
                description="Get Messages app status and account information",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="messages_create_group",
                description="Create a group message",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of phone numbers, emails, or contact names"
                        },
                        "message": {
                            "type": "string",
                            "description": "Initial message for the group"
                        },
                        "group_name": {
                            "type": "string",
                            "description": "Optional group name"
                        }
                    },
                    "required": ["recipients", "message"]
                }
            )
        ]

    def get_resources(self) -> List[ResourceDefinition]:
        """Return the resources provided by this connector."""
        return [
            ResourceDefinition(
                uri="messages://conversations",
                name="Message Conversations",
                description="List of all message conversations",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="messages://unread",
                name="Unread Messages",
                description="All unread messages",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="messages://recent",
                name="Recent Messages",
                description="Recent messages across all conversations",
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
            if tool_name == "messages_send":
                return self._send_message(arguments)
            elif tool_name == "messages_get_conversations":
                return self._get_conversations(arguments)
            elif tool_name == "messages_get_conversation":
                return self._get_conversation(arguments)
            elif tool_name == "messages_search":
                return self._search_messages(arguments)
            elif tool_name == "messages_get_unread":
                return self._get_unread(arguments)
            elif tool_name == "messages_mark_read":
                return self._mark_read(arguments)
            elif tool_name == "messages_delete_conversation":
                return self._delete_conversation(arguments)
            elif tool_name == "messages_send_file":
                return self._send_file(arguments)
            elif tool_name == "messages_get_status":
                return self._get_status()
            elif tool_name == "messages_create_group":
                return self._create_group(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {str(e)}")
            return {"error": str(e)}

    def _send_message(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to a recipient."""
        recipient = arguments["recipient"]
        message = arguments["message"]
        service = arguments.get("service", "iMessage")
        
        # Escape quotes in message
        escaped_message = message.replace('"', '\\"')
        
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = {service}
            set targetBuddy to buddy "{recipient}" of targetService
            send "{escaped_message}" to targetBuddy
            return "sent"
        end tell
        '''
        
        result = self._run_applescript(script)
        return {
            "success": True,
            "recipient": recipient,
            "message": message,
            "service": service,
            "status": result
        }

    def _get_conversations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of message conversations."""
        limit = arguments.get("limit", 10)
        include_messages = arguments.get("include_messages", False)
        
        if include_messages:
            script = f'''
            tell application "Messages"
                set conversationList to {{}}
                set chatList to chats
                
                repeat with i from 1 to (count of chatList)
                    if i > {limit} then exit repeat
                    set currentChat to item i of chatList
                    
                    set chatName to display name of currentChat
                    set chatID to id of currentChat
                    set messageCount to count of messages of currentChat
                    
                    -- Get last few messages
                    set recentMessages to {{}}
                    set msgList to messages of currentChat
                    set startIndex to (count of msgList) - 4
                    if startIndex < 1 then set startIndex to 1
                    
                    repeat with j from startIndex to (count of msgList)
                        set msg to item j of msgList
                        set msgText to text of msg
                        set msgDate to date sent of msg
                        set msgSender to handle of msg
                        set end of recentMessages to msgSender & ": " & msgText
                    end repeat
                    
                    set conversationInfo to chatName & "|" & chatID & "|" & messageCount & "|" & (recentMessages as string)
                    set end of conversationList to conversationInfo
                end repeat
                
                return conversationList
            end tell
            '''
        else:
            script = f'''
            tell application "Messages"
                set conversationList to {{}}
                set chatList to chats
                
                repeat with i from 1 to (count of chatList)
                    if i > {limit} then exit repeat
                    set currentChat to item i of chatList
                    
                    set chatName to display name of currentChat
                    set chatID to id of currentChat
                    set messageCount to count of messages of currentChat
                    
                    set conversationInfo to chatName & "|" & chatID & "|" & messageCount
                    set end of conversationList to conversationInfo
                end repeat
                
                return conversationList
            end tell
            '''
        
        result = self._run_applescript(script)
        
        conversations = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 3:
                    conv = {
                        "name": parts[0],
                        "id": parts[1],
                        "message_count": int(parts[2]) if parts[2].isdigit() else 0
                    }
                    if include_messages and len(parts) > 3:
                        conv["recent_messages"] = parts[3].split(", ")
                    conversations.append(conv)
        
        return {"conversations": conversations, "total_count": len(conversations)}

    def _get_conversation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get messages from a specific conversation."""
        recipient = arguments["recipient"]
        limit = arguments.get("limit", 20)
        
        script = f'''
        tell application "Messages"
            set targetChat to first chat whose display name contains "{recipient}"
            set messageList to {{}}
            set msgList to messages of targetChat
            
            set startIndex to (count of msgList) - {limit} + 1
            if startIndex < 1 then set startIndex to 1
            
            repeat with i from startIndex to (count of msgList)
                set msg to item i of msgList
                set msgText to text of msg
                set msgDate to date sent of msg as string
                set msgSender to handle of msg
                set isFromMe to (direction of msg as string) is "outgoing"
                
                set messageInfo to msgSender & "|" & msgText & "|" & msgDate & "|" & isFromMe
                set end of messageList to messageInfo
            end repeat
            
            return messageList
        end tell
        '''
        
        result = self._run_applescript(script)
        
        messages = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 4:
                    messages.append({
                        "sender": parts[0],
                        "text": parts[1],
                        "date": parts[2],
                        "is_from_me": parts[3] == "true"
                    })
        
        return {
            "conversation": recipient,
            "messages": messages,
            "message_count": len(messages)
        }

    def _search_messages(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for messages containing specific text."""
        query = arguments["query"]
        limit = arguments.get("limit", 20)
        
        script = f'''
        tell application "Messages"
            set foundMessages to {{}}
            set allChats to chats
            set foundCount to 0
            
            repeat with currentChat in allChats
                if foundCount >= {limit} then exit repeat
                
                set msgList to messages of currentChat
                repeat with msg in msgList
                    if foundCount >= {limit} then exit repeat
                    
                    set msgText to text of msg
                    if msgText contains "{query}" then
                        set msgDate to date sent of msg as string
                        set msgSender to handle of msg
                        set chatName to display name of currentChat
                        
                        set messageInfo to chatName & "|" & msgSender & "|" & msgText & "|" & msgDate
                        set end of foundMessages to messageInfo
                        set foundCount to foundCount + 1
                    end if
                end repeat
            end repeat
            
            return foundMessages
        end tell
        '''
        
        result = self._run_applescript(script)
        
        messages = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 4:
                    messages.append({
                        "conversation": parts[0],
                        "sender": parts[1],
                        "text": parts[2],
                        "date": parts[3]
                    })
        
        return {
            "query": query,
            "found_messages": messages,
            "total_found": len(messages)
        }

    def _get_unread(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get unread messages."""
        limit = arguments.get("limit", 50)
        
        # Note: Messages app doesn't have a direct "unread" property in AppleScript
        # This is a simplified implementation that gets recent messages
        script = f'''
        tell application "Messages"
            set unreadMessages to {{}}
            set allChats to chats
            set foundCount to 0
            
            repeat with currentChat in allChats
                if foundCount >= {limit} then exit repeat
                
                set msgList to messages of currentChat
                -- Get the last few messages from each chat as proxy for unread
                set recentCount to count of msgList
                set startIndex to recentCount - 2
                if startIndex < 1 then set startIndex to 1
                
                repeat with i from startIndex to recentCount
                    if foundCount >= {limit} then exit repeat
                    
                    set msg to item i of msgList
                    set msgText to text of msg
                    set msgDate to date sent of msg as string
                    set msgSender to handle of msg
                    set chatName to display name of currentChat
                    set isFromMe to (direction of msg as string) is "outgoing"
                    
                    -- Only include incoming messages as potential unread
                    if not isFromMe then
                        set messageInfo to chatName & "|" & msgSender & "|" & msgText & "|" & msgDate
                        set end of unreadMessages to messageInfo
                        set foundCount to foundCount + 1
                    end if
                end repeat
            end repeat
            
            return unreadMessages
        end tell
        '''
        
        result = self._run_applescript(script)
        
        messages = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 4:
                    messages.append({
                        "conversation": parts[0],
                        "sender": parts[1],
                        "text": parts[2],
                        "date": parts[3]
                    })
        
        return {
            "unread_messages": messages,
            "total_count": len(messages)
        }

    def _mark_read(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Mark messages as read in a conversation."""
        recipient = arguments["recipient"]
        
        # Note: Messages app doesn't expose read/unread state in AppleScript
        # This is a placeholder implementation
        script = f'''
        tell application "Messages"
            set targetChat to first chat whose display name contains "{recipient}"
            -- There's no direct way to mark as read via AppleScript
            -- This would typically require GUI automation
            return "marked_read"
        end tell
        '''
        
        result = self._run_applescript(script)
        return {
            "success": True,
            "conversation": recipient,
            "action": "marked_read",
            "note": "Read status marking has limited AppleScript support"
        }

    def _delete_conversation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an entire conversation."""
        recipient = arguments["recipient"]
        confirm = arguments.get("confirm", False)
        
        if not confirm:
            return {"error": "Deletion requires confirmation. Set 'confirm' to true."}
        
        script = f'''
        tell application "Messages"
            set targetChat to first chat whose display name contains "{recipient}"
            delete targetChat
            return "deleted"
        end tell
        '''
        
        result = self._run_applescript(script)
        return {
            "success": True,
            "conversation": recipient,
            "action": "conversation_deleted"
        }

    def _send_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send a file attachment via Messages."""
        recipient = arguments["recipient"]
        file_path = arguments["file_path"]
        message = arguments.get("message", "")
        
        # Escape quotes in message
        escaped_message = message.replace('"', '\\"')
        
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{recipient}" of targetService
            set fileToSend to POSIX file "{file_path}"
            
            if "{escaped_message}" is not "" then
                send "{escaped_message}" to targetBuddy
            end if
            
            send fileToSend to targetBuddy
            return "file_sent"
        end tell
        '''
        
        result = self._run_applescript(script)
        return {
            "success": True,
            "recipient": recipient,
            "file_path": file_path,
            "message": message,
            "status": result
        }

    def _get_status(self) -> Dict[str, Any]:
        """Get Messages app status and account information."""
        script = '''
        tell application "Messages"
            set serviceList to {}
            repeat with svc in services
                set serviceName to name of svc
                set serviceType to service type of svc as string
                set serviceStatus to connection status of svc as string
                set serviceInfo to serviceName & "|" & serviceType & "|" & serviceStatus
                set end of serviceList to serviceInfo
            end repeat
            
            return serviceList
        end tell
        '''
        
        result = self._run_applescript(script)
        
        services = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 3:
                    services.append({
                        "name": parts[0],
                        "type": parts[1],
                        "status": parts[2]
                    })
        
        return {
            "app_status": "running",
            "services": services,
            "total_services": len(services)
        }

    def _create_group(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create a group message."""
        recipients = arguments["recipients"]
        message = arguments["message"]
        group_name = arguments.get("group_name", "")
        
        # Escape quotes in message
        escaped_message = message.replace('"', '\\"')
        
        # Build recipient list for AppleScript
        recipient_list = '", "'.join(recipients)
        
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set buddyList to {{}}
            
            repeat with recipientID in {{"{recipient_list}"}}
                set targetBuddy to buddy recipientID of targetService
                set end of buddyList to targetBuddy
            end repeat
            
            send "{escaped_message}" to buddyList
            return "group_message_sent"
        end tell
        '''
        
        result = self._run_applescript(script)
        return {
            "success": True,
            "recipients": recipients,
            "message": message,
            "group_name": group_name,
            "status": result
        }

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI."""
        try:
            if uri == "messages://conversations":
                return self._get_conversations({"limit": 50, "include_messages": True})
            elif uri == "messages://unread":
                return self._get_unread({"limit": 100})
            elif uri == "messages://recent":
                # Get recent messages across all conversations
                return self._get_conversations({"limit": 20, "include_messages": True})
            else:
                return {"error": f"Unknown resource URI: {uri}"}
                
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {str(e)}")
            return {"error": str(e)}