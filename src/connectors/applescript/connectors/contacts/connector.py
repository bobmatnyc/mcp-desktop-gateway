"""
Contacts AppleScript Connector

Provides comprehensive Contacts app automation through AppleScript.
"""

import logging
import subprocess
from typing import Dict, List, Any, Optional

from core.base_connector import BaseConnector
from core.models import ToolDefinition, ResourceDefinition

logger = logging.getLogger(__name__)


class ContactsConnector(BaseConnector):
    """Contacts app automation connector using AppleScript."""

    def __init__(self):
        super().__init__()
        self.app_name = "Contacts"

    def get_tools(self) -> List[ToolDefinition]:
        """Return the tools provided by this connector."""
        return [
            ToolDefinition(
                name="contacts_search",
                description="Search for contacts by name, email, or phone",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (name, email, or phone)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            ToolDefinition(
                name="contacts_get_contact",
                description="Get detailed information about a specific contact",
                input_schema={
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "Full name of the contact"
                        },
                        "contact_id": {
                            "type": "string",
                            "description": "Contact ID (alternative to name)"
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="contacts_create_contact",
                description="Create a new contact",
                input_schema={
                    "type": "object",
                    "properties": {
                        "first_name": {
                            "type": "string",
                            "description": "First name"
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Last name"
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Phone number"
                        },
                        "company": {
                            "type": "string",
                            "description": "Company name"
                        },
                        "job_title": {
                            "type": "string",
                            "description": "Job title"
                        }
                    },
                    "required": ["first_name"]
                }
            ),
            ToolDefinition(
                name="contacts_update_contact",
                description="Update an existing contact",
                input_schema={
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "Full name of the contact to update"
                        },
                        "first_name": {
                            "type": "string",
                            "description": "New first name"
                        },
                        "last_name": {
                            "type": "string",
                            "description": "New last name"
                        },
                        "email": {
                            "type": "string",
                            "description": "New email address"
                        },
                        "phone": {
                            "type": "string",
                            "description": "New phone number"
                        },
                        "company": {
                            "type": "string",
                            "description": "New company name"
                        },
                        "job_title": {
                            "type": "string",
                            "description": "New job title"
                        }
                    },
                    "required": ["contact_name"]
                }
            ),
            ToolDefinition(
                name="contacts_delete_contact",
                description="Delete a contact",
                input_schema={
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "Full name of the contact to delete"
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": "Confirmation required to delete (default: false)",
                            "default": False
                        }
                    },
                    "required": ["contact_name"]
                }
            ),
            ToolDefinition(
                name="contacts_get_groups",
                description="Get list of contact groups",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="contacts_create_group",
                description="Create a new contact group",
                input_schema={
                    "type": "object",
                    "properties": {
                        "group_name": {
                            "type": "string",
                            "description": "Name of the new group"
                        }
                    },
                    "required": ["group_name"]
                }
            ),
            ToolDefinition(
                name="contacts_add_to_group",
                description="Add a contact to a group",
                input_schema={
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "Full name of the contact"
                        },
                        "group_name": {
                            "type": "string",
                            "description": "Name of the group"
                        }
                    },
                    "required": ["contact_name", "group_name"]
                }
            ),
            ToolDefinition(
                name="contacts_export_vcard",
                description="Export contact(s) as vCard file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "contact_name": {
                            "type": "string",
                            "description": "Contact name to export (exports all if not specified)"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Output file path (default: ~/Desktop/contacts.vcf)"
                        }
                    },
                    "required": []
                }
            ),
            ToolDefinition(
                name="contacts_get_recent",
                description="Get recently contacted people",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10)",
                            "default": 10
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
                uri="contacts://all",
                name="All Contacts",
                description="List of all contacts",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="contacts://groups",
                name="Contact Groups",
                description="List of all contact groups",
                mimeType="application/json"
            ),
            ResourceDefinition(
                uri="contacts://recent",
                name="Recent Contacts",
                description="Recently contacted people",
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
            if tool_name == "contacts_search":
                return self._search_contacts(arguments)
            elif tool_name == "contacts_get_contact":
                return self._get_contact(arguments)
            elif tool_name == "contacts_create_contact":
                return self._create_contact(arguments)
            elif tool_name == "contacts_update_contact":
                return self._update_contact(arguments)
            elif tool_name == "contacts_delete_contact":
                return self._delete_contact(arguments)
            elif tool_name == "contacts_get_groups":
                return self._get_groups()
            elif tool_name == "contacts_create_group":
                return self._create_group(arguments)
            elif tool_name == "contacts_add_to_group":
                return self._add_to_group(arguments)
            elif tool_name == "contacts_export_vcard":
                return self._export_vcard(arguments)
            elif tool_name == "contacts_get_recent":
                return self._get_recent(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Error executing {tool_name}: {str(e)}")
            return {"error": str(e)}

    def _search_contacts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for contacts."""
        query = arguments["query"]
        limit = arguments.get("limit", 10)
        
        script = f'''
        tell application "Contacts"
            set foundContacts to {{}}
            set contactList to people whose name contains "{query}" or ¬
                (exists email) and (value of email contains "{query}") or ¬
                (exists phone) and (value of phone contains "{query}")
            
            repeat with i from 1 to (count of contactList)
                if i > {limit} then exit repeat
                set contactInfo to item i of contactList
                set contactName to name of contactInfo
                set contactID to id of contactInfo
                
                set emailList to {{}}
                repeat with emailAddr in emails of contactInfo
                    set end of emailList to (value of emailAddr)
                end repeat
                
                set phoneList to {{}}
                repeat with phoneNum in phones of contactInfo
                    set end of phoneList to (value of phoneNum)
                end repeat
                
                set contactDetails to contactName & "|" & contactID & "|" & ¬
                    (emailList as string) & "|" & (phoneList as string)
                set end of foundContacts to contactDetails
            end repeat
            
            return foundContacts
        end tell
        '''
        
        result = self._run_applescript(script)
        
        # Parse the result
        contacts = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 4:
                    contacts.append({
                        "name": parts[0].strip(),
                        "id": parts[1].strip(),
                        "emails": [e.strip() for e in parts[2].split(", ") if e.strip()],
                        "phones": [p.strip() for p in parts[3].split(", ") if p.strip()]
                    })
        
        return {"contacts": contacts, "query": query, "total_found": len(contacts)}

    def _get_contact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a contact."""
        contact_name = arguments.get("contact_name")
        contact_id = arguments.get("contact_id")
        
        if contact_name:
            search_criteria = f'whose name is "{contact_name}"'
        elif contact_id:
            search_criteria = f'whose id is "{contact_id}"'
        else:
            return {"error": "Either contact_name or contact_id must be provided"}
        
        script = f'''
        tell application "Contacts"
            set targetContact to first person {search_criteria}
            
            set contactName to name of targetContact
            set contactID to id of targetContact
            
            set firstName to ""
            set lastName to ""
            set company to ""
            set jobTitle to ""
            
            try
                set firstName to first name of targetContact
            end try
            try
                set lastName to last name of targetContact
            end try
            try
                set company to organization of targetContact
            end try
            try
                set jobTitle to job title of targetContact
            end try
            
            set emailList to {{}}
            repeat with emailAddr in emails of targetContact
                set emailLabel to (label of emailAddr) as string
                set emailValue to (value of emailAddr) as string
                set end of emailList to emailLabel & ":" & emailValue
            end repeat
            
            set phoneList to {{}}
            repeat with phoneNum in phones of targetContact
                set phoneLabel to (label of phoneNum) as string
                set phoneValue to (value of phoneNum) as string
                set end of phoneList to phoneLabel & ":" & phoneValue
            end repeat
            
            set addressList to {{}}
            repeat with addr in addresses of targetContact
                set addrLabel to (label of addr) as string
                set addrValue to (formatted address of addr) as string
                set end of addressList to addrLabel & ":" & addrValue
            end repeat
            
            return contactName & "|" & contactID & "|" & firstName & "|" & lastName & "|" & ¬
                company & "|" & jobTitle & "|" & ¬
                (emailList as string) & "|" & (phoneList as string) & "|" & (addressList as string)
        end tell
        '''
        
        result = self._run_applescript(script)
        
        # Parse the result
        parts = result.split("|")
        if len(parts) >= 9:
            emails = {}
            phones = {}
            addresses = {}
            
            # Parse emails
            if parts[6]:
                for email_item in parts[6].split(", "):
                    if ":" in email_item:
                        label, value = email_item.split(":", 1)
                        emails[label] = value
            
            # Parse phones
            if parts[7]:
                for phone_item in parts[7].split(", "):
                    if ":" in phone_item:
                        label, value = phone_item.split(":", 1)
                        phones[label] = value
            
            # Parse addresses
            if parts[8]:
                for addr_item in parts[8].split(", "):
                    if ":" in addr_item:
                        label, value = addr_item.split(":", 1)
                        addresses[label] = value
            
            contact_info = {
                "name": parts[0],
                "id": parts[1],
                "first_name": parts[2],
                "last_name": parts[3],
                "company": parts[4],
                "job_title": parts[5],
                "emails": emails,
                "phones": phones,
                "addresses": addresses
            }
            
            return {"contact": contact_info}
        else:
            return {"error": "Contact not found or error parsing contact data"}

    def _create_contact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact."""
        first_name = arguments["first_name"]
        last_name = arguments.get("last_name", "")
        email = arguments.get("email", "")
        phone = arguments.get("phone", "")
        company = arguments.get("company", "")
        job_title = arguments.get("job_title", "")
        
        script = f'''
        tell application "Contacts"
            set newContact to make new person
            set first name of newContact to "{first_name}"
            
            if "{last_name}" is not "" then
                set last name of newContact to "{last_name}"
            end if
            
            if "{company}" is not "" then
                set organization of newContact to "{company}"
            end if
            
            if "{job_title}" is not "" then
                set job title of newContact to "{job_title}"
            end if
            
            if "{email}" is not "" then
                make new email at end of emails of newContact with properties {{label:"work", value:"{email}"}}
            end if
            
            if "{phone}" is not "" then
                make new phone at end of phones of newContact with properties {{label:"work", value:"{phone}"}}
            end if
            
            save
            return name of newContact & "|" & id of newContact
        end tell
        '''
        
        result = self._run_applescript(script)
        parts = result.split("|")
        
        return {
            "success": True,
            "contact": {
                "name": parts[0] if len(parts) > 0 else "",
                "id": parts[1] if len(parts) > 1 else "",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "company": company,
                "job_title": job_title
            }
        }

    def _update_contact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing contact."""
        contact_name = arguments["contact_name"]
        
        # Build update script dynamically based on provided fields
        updates = []
        
        if "first_name" in arguments:
            updates.append(f'set first name of targetContact to "{arguments["first_name"]}"')
        if "last_name" in arguments:
            updates.append(f'set last name of targetContact to "{arguments["last_name"]}"')
        if "company" in arguments:
            updates.append(f'set organization of targetContact to "{arguments["company"]}"')
        if "job_title" in arguments:
            updates.append(f'set job title of targetContact to "{arguments["job_title"]}"')
        
        update_script = "\n".join(updates)
        
        script = f'''
        tell application "Contacts"
            set targetContact to first person whose name is "{contact_name}"
            
            {update_script}
            
            save
            return name of targetContact
        end tell
        '''
        
        result = self._run_applescript(script)
        return {"success": True, "updated_contact": result}

    def _delete_contact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a contact."""
        contact_name = arguments["contact_name"]
        confirm = arguments.get("confirm", False)
        
        if not confirm:
            return {"error": "Deletion requires confirmation. Set 'confirm' to true."}
        
        script = f'''
        tell application "Contacts"
            delete (first person whose name is "{contact_name}")
            save
            return "deleted"
        end tell
        '''
        
        self._run_applescript(script)
        return {"success": True, "action": "contact_deleted", "contact_name": contact_name}

    def _get_groups(self) -> Dict[str, Any]:
        """Get list of contact groups."""
        script = '''
        tell application "Contacts"
            set groupList to {}
            repeat with grp in groups
                set groupName to name of grp
                set groupID to id of grp
                set memberCount to count of people of grp
                set end of groupList to groupName & "|" & groupID & "|" & memberCount
            end repeat
            return groupList
        end tell
        '''
        
        result = self._run_applescript(script)
        
        groups = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 3:
                    groups.append({
                        "name": parts[0],
                        "id": parts[1],
                        "member_count": int(parts[2]) if parts[2].isdigit() else 0
                    })
        
        return {"groups": groups, "total_count": len(groups)}

    def _create_group(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contact group."""
        group_name = arguments["group_name"]
        
        script = f'''
        tell application "Contacts"
            set newGroup to make new group with properties {{name:"{group_name}"}}
            save
            return name of newGroup & "|" & id of newGroup
        end tell
        '''
        
        result = self._run_applescript(script)
        parts = result.split("|")
        
        return {
            "success": True,
            "group": {
                "name": parts[0] if len(parts) > 0 else "",
                "id": parts[1] if len(parts) > 1 else ""
            }
        }

    def _add_to_group(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add a contact to a group."""
        contact_name = arguments["contact_name"]
        group_name = arguments["group_name"]
        
        script = f'''
        tell application "Contacts"
            set targetContact to first person whose name is "{contact_name}"
            set targetGroup to first group whose name is "{group_name}"
            add targetContact to targetGroup
            save
            return "added"
        end tell
        '''
        
        self._run_applescript(script)
        return {
            "success": True,
            "action": "added_to_group",
            "contact_name": contact_name,
            "group_name": group_name
        }

    def _export_vcard(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Export contact(s) as vCard file."""
        contact_name = arguments.get("contact_name")
        output_path = arguments.get("output_path", "~/Desktop/contacts.vcf")
        
        if contact_name:
            script = f'''
            tell application "Contacts"
                set targetContact to first person whose name is "{contact_name}"
                set vcardData to vcard of targetContact
                
                set outputFile to open for access POSIX file "{output_path}" with write permission
                write vcardData to outputFile
                close access outputFile
                
                return "exported_single"
            end tell
            '''
        else:
            # Export all contacts (this might be a large operation)
            script = f'''
            tell application "Contacts"
                set allContacts to people
                set vcardData to ""
                
                repeat with contact in allContacts
                    set vcardData to vcardData & vcard of contact
                end repeat
                
                set outputFile to open for access POSIX file "{output_path}" with write permission
                write vcardData to outputFile
                close access outputFile
                
                return "exported_all"
            end tell
            '''
        
        result = self._run_applescript(script)
        return {
            "success": True,
            "action": result,
            "output_path": output_path,
            "contact_name": contact_name
        }

    def _get_recent(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get recently contacted people."""
        limit = arguments.get("limit", 10)
        
        # Note: This is a simplified version. True recent contacts would require
        # accessing communication history from Mail, Messages, etc.
        script = f'''
        tell application "Contacts"
            set recentContacts to {{}}
            set contactList to people
            
            -- Get first {limit} contacts as a proxy for recent
            -- In reality, you'd want to sort by last contact date
            repeat with i from 1 to (count of contactList)
                if i > {limit} then exit repeat
                set contactInfo to item i of contactList
                set contactName to name of contactInfo
                set contactID to id of contactInfo
                set end of recentContacts to contactName & "|" & contactID
            end repeat
            
            return recentContacts
        end tell
        '''
        
        result = self._run_applescript(script)
        
        contacts = []
        if result and result != "{}":
            lines = result.split(", ")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 2:
                    contacts.append({
                        "name": parts[0],
                        "id": parts[1]
                    })
        
        return {"recent_contacts": contacts, "limit": limit}

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource by URI."""
        try:
            if uri == "contacts://all":
                return self._search_contacts({"query": "", "limit": 100})
            elif uri == "contacts://groups":
                return self._get_groups()
            elif uri == "contacts://recent":
                return self._get_recent({"limit": 20})
            else:
                return {"error": f"Unknown resource URI: {uri}"}
                
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {str(e)}")
            return {"error": str(e)}