# Getting Started with MCP Desktop Gateway

This guide shows practical examples of what you can accomplish with the MCP Desktop Gateway in Claude Desktop.

## Installation

First, install the gateway globally:

```bash
npm install -g @bobmatnyc/mcp-desktop-gateway
```

Then configure Claude Desktop to use the gateway. You can do this automatically with our install script:

```bash
# Download and run the configuration script
curl -sSL https://raw.githubusercontent.com/bobmatnyc/mcp-desktop-gateway/main/scripts/install-claude-config.sh | bash
```

Or manually add it to your Claude Desktop configuration in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-desktop-gateway": {
      "command": "mcp-desktop-gateway"
    }
  }
}
```

The install script will:
- ✅ Verify the gateway is installed
- ✅ Backup your existing Claude config
- ✅ Add/update the MCP server configuration
- ✅ Validate the JSON configuration
- ✅ Test the gateway functionality

## What You Can Do

### 🖥️ System Automation

**Execute shell commands and scripts:**
```
"Run a system update and show me the status"
"Check my disk usage and free up space if needed"
"Find all Python files in my project directory"
"Create a backup of my important files"
```

**File and directory operations:**
```
"List all files in my Downloads folder from the last 7 days"
"Find large files taking up space on my system"
"Search for files containing 'config' in their name"
"Show me the contents of my project's README file"
```

### 🌐 Web Browser Control (macOS)

**Automate Safari browsing:**
```
"Open GitHub and navigate to my repositories"
"Take a screenshot of the current webpage"
"Execute JavaScript to extract all links from this page"
"Open multiple tabs with my daily reading list"
"Get the title and URL of all open Safari tabs"
```

**Web development workflows:**
```
"Open localhost:3000 in a new Safari tab"
"Refresh all tabs containing 'localhost'"
"Extract form data from the current webpage"
"Navigate through my bookmarks to find development resources"
```

### 📞 Communication Automation (macOS)

**Contacts management:**
```
"Find all contacts from my company domain"
"Create a new contact for John Doe with phone 555-0123"
"Show me all contacts in the 'Work' group"
"Update the phone number for Sarah Smith"
```

**Messages automation:**
```
"Send a text message to my team about the meeting"
"Get my recent message conversations"
"Check if I have any unread messages"
"Send a follow-up message to the last conversation"
```

### 📁 File Management (macOS)

**Finder operations:**
```
"Open my Documents folder and show recent files"
"Create a new folder called 'Project Archives'"
"Move all PDF files from Downloads to Documents"
"Show me the properties of this file"
"Find all images in my Photos directory"
```

**File organization:**
```
"Organize my Downloads folder by file type"
"Find duplicate files in my Documents"
"Create a folder structure for my new project"
"Archive old files to a backup location"
```

### 🔧 Development Workflows

**Project management:**
```
"Run tests in my current project directory"
"Check the status of my Git repository"
"Install npm dependencies and start the development server"
"Format my code and run the linter"
```

**Environment setup:**
```
"Create a new Python virtual environment"
"Check which Python packages are installed"
"Set up a new React project with TypeScript"
"Configure my development environment"
```

### 📊 System Monitoring

**Performance monitoring:**
```
"Show me current CPU and memory usage"
"Check which processes are using the most resources"
"Monitor disk space across all drives"
"Display network connection status"
```

**System information:**
```
"Get detailed system information"
"Show me installed software versions"
"Check my current network configuration"
"Display environment variables"
```

## Advanced Automation Examples

### Daily Workflow Automation

```
"Help me start my workday:
1. Open my project directory in Finder
2. Launch Safari with my daily dashboard tabs
3. Check for any urgent messages
4. Show me today's calendar in Contacts
5. Run git status on my active projects"
```

### Content Creation Pipeline

```
"Set up my content creation workflow:
1. Create a new folder for today's blog post
2. Open my writing template in the default editor
3. Take a screenshot of my inspiration board
4. Start my time tracking for this project"
```

### Development Environment Setup

```
"Prepare my development environment:
1. Navigate to my projects directory
2. Create a new Git repository
3. Set up the initial file structure
4. Install dependencies from package.json
5. Open the project in my default code editor"
```

### File Organization and Cleanup

```
"Clean up my computer:
1. Find large files over 100MB
2. Move old downloads to archive folder
3. Clear temporary files and caches
4. Organize desktop files into appropriate folders
5. Update my backup system"
```

## Tips for Best Results

### 🎯 Be Specific
Instead of: *"Send a message"*  
Try: *"Send a text message to Sarah saying 'Meeting moved to 3 PM'"*

### 🔗 Chain Actions
Instead of multiple separate requests:  
Try: *"Open my project folder, run git status, and start the development server"*

### 🛡️ Safety First
The gateway includes built-in safety features:
- Command validation and filtering
- Timeout protection
- Secure execution environment
- Permission-based access control

### 🔄 Combine Tools
Mix different connector capabilities:
```
"Create a project status report:
1. Get git status from my development folder
2. Take a screenshot of my current Safari tab
3. Send a summary message to my team
4. Save the report to my Documents folder"
```

## Available Connectors

| Connector | Description | Platform |
|-----------|-------------|----------|
| **Shell** | Execute commands, file operations, system info | All |
| **AppleScript** | macOS app automation (Safari, Contacts, Messages, Finder) | macOS |
| **Gateway Utils** | Connector management, system diagnostics | All |
| **Hello World** | Testing and examples | All |

## Troubleshooting

### Gateway Not Responding
```
"Check the status of all MCP connectors"
"Restart the gateway service"
"Show me the gateway logs"
```

### Permission Issues
```
"List available tools and their permissions"
"Check if I have access to run shell commands"
"Verify my system permissions"
```

### Performance Issues
```
"Show me gateway performance metrics"
"Check system resource usage"
"Optimize the gateway configuration"
```

## Next Steps

1. **Explore Tools**: Ask *"What tools are available?"* to see all capabilities
2. **Check Resources**: Use *"Show me available resources"* for system information
3. **Get Help**: Request *"Show me the gateway documentation"* for detailed guides
4. **Custom Scripts**: Create your own automation scripts in the user-scripts directory

## Security Notes

- All commands are validated before execution
- Dangerous operations require explicit confirmation
- File access is controlled and logged
- Network operations are monitored

The MCP Desktop Gateway provides a secure, powerful bridge between Claude and your desktop environment. Start with simple commands and gradually build more complex automation workflows as you become comfortable with the system.

---

*For more advanced usage and configuration options, see the full documentation in `/docs/PROJECT.md`*