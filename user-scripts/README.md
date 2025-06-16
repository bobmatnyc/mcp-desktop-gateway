# User Scripts Directory

This directory contains ad-hoc code created based on user requests. Scripts are organized by task and language for easy management and reuse.

## Directory Structure

```
user-scripts/
├── python/           # Python scripts and modules
│   ├── active/       # Currently used/maintained scripts
│   ├── archived/     # Old or deprecated scripts  
│   └── templates/    # Reusable script templates
├── javascript/       # JavaScript/Node.js scripts
│   ├── active/       # Currently used/maintained scripts
│   ├── archived/     # Old or deprecated scripts
│   └── templates/    # Reusable script templates
├── shell/           # Shell scripts and utilities
│   ├── active/       # Currently used/maintained scripts
│   ├── archived/     # Old or deprecated scripts
│   └── templates/    # Reusable script templates
├── applescript/     # AppleScript automation (macOS only)
│   ├── active/       # Currently used/maintained scripts
│   ├── archived/     # Old or deprecated scripts
│   └── templates/    # Reusable script templates
├── shared/          # Shared resources across all scripts
│   ├── data/        # Common data files
│   ├── configs/     # Configuration files
│   └── logs/        # Script execution logs
└── README.md        # This file
```

## Naming Conventions

### Script Files
Scripts should follow this naming pattern:
```
YYYY-MM-DD_<task-name>_<language>.<ext>
```

Examples:
- `2025-06-16_file-processor_python.py`
- `2025-06-16_api-client_javascript.js`  
- `2025-06-16_backup-script_shell.sh`
- `2025-06-16_app-automation_applescript.applescript`

### Task Directories
For complex tasks with multiple files:
```
YYYY-MM-DD_<task-name>/
├── README.md              # Task description and usage
├── main.<ext>            # Primary script file
├── requirements.txt      # Dependencies (Python)
├── package.json          # Dependencies (Node.js)
└── config/              # Task-specific config files
```

## Documentation Requirements

Every script or task directory must include:

1. **Header comment** with:
   - Task description
   - Creation date
   - Usage instructions
   - Dependencies
   - Author/Creator info

2. **README.md** (for multi-file tasks) with:
   - Purpose and context
   - Installation/setup steps
   - Usage examples
   - Input/output specifications
   - Known limitations

## Usage Guidelines

### Adding New Scripts

1. **Determine the appropriate location**:
   - Single file → `<language>/active/`
   - Multi-file task → `<language>/active/<task-name>/`

2. **Follow naming conventions** as outlined above

3. **Add proper documentation** in comments and README

4. **Test thoroughly** before committing to active directory

### Managing Scripts

- **Active**: Scripts currently in use or recently created
- **Archived**: Scripts no longer needed but kept for reference
- **Templates**: Reusable patterns for common tasks

### Shared Resources

- **data/**: Common datasets, lookup tables, reference files
- **configs/**: Shared configuration templates and examples
- **logs/**: Execution logs for debugging and monitoring

## Script Templates

See the `templates/` directory in each language folder for:
- Basic script structure
- Common import patterns
- Error handling examples
- Documentation templates

## Security Guidelines

1. **Never commit sensitive data** (passwords, API keys, personal info)
2. **Use environment variables** for configuration
3. **Validate inputs** and handle errors gracefully
4. **Follow least privilege principle** in file permissions
5. **Review code** for security issues before deployment

## Best Practices

### Python Scripts
- Use virtual environments for dependencies
- Follow PEP 8 style guidelines
- Include type hints where helpful
- Use logging instead of print statements

### JavaScript Scripts
- Use modern ES6+ syntax
- Include package.json for dependencies
- Use proper error handling
- Follow consistent formatting

### Shell Scripts
- Use `#!/bin/bash` shebang
- Set `set -euo pipefail` for safety
- Quote variables properly
- Include usage help (`-h` flag)

### AppleScript Scripts
- Include proper error handling
- Use logging for debugging
- Test on target macOS version
- Handle application availability gracefully

## Integration with MCP Desktop Gateway

User scripts can be accessed through the shell connector:

```python
# Execute Python script
execute_command(command="python user-scripts/python/active/my-script.py")

# Execute Node.js script  
execute_command(command="node user-scripts/javascript/active/my-script.js")

# Execute shell script
execute_command(command="bash user-scripts/shell/active/my-script.sh")

# Execute AppleScript (macOS only)
execute_command(command="osascript user-scripts/applescript/active/my-script.applescript")
```

## Examples

See individual template files for language-specific examples and patterns.