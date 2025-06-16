#!/usr/bin/env python3
"""
User Scripts Management Utility

This script helps manage user-generated scripts in the MCP Desktop Gateway project.
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent
USER_SCRIPTS_DIR = PROJECT_ROOT / "user-scripts"

SUPPORTED_LANGUAGES = {
    'python': {'ext': '.py', 'dir': 'python'},
    'javascript': {'ext': '.js', 'dir': 'javascript'},
    'shell': {'ext': '.sh', 'dir': 'shell'},
    'applescript': {'ext': '.applescript', 'dir': 'applescript'}
}

def get_script_info(script_path: Path) -> Dict:
    """Extract metadata from script file."""
    info = {
        'name': script_path.name,
        'path': str(script_path),
        'size': script_path.stat().st_size,
        'modified': datetime.fromtimestamp(script_path.stat().st_mtime),
        'language': None,
        'description': None
    }
    
    # Determine language from path
    for lang, config in SUPPORTED_LANGUAGES.items():
        if script_path.suffix == config['ext'] and config['dir'] in str(script_path):
            info['language'] = lang
            break
    
    # Try to extract description from file header
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:20]  # Read first 20 lines
            
        for line in lines:
            line = line.strip()
            if line.startswith('#') or line.startswith('//') or line.startswith('(*'):
                if 'Task:' in line or 'Description:' in line:
                    # Extract description after the marker
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        info['description'] = parts[1].strip()
                        break
    except Exception:
        pass
    
    return info

def list_scripts(language: Optional[str] = None, category: str = 'active') -> List[Dict]:
    """List all scripts in the specified category."""
    scripts = []
    
    languages = [language] if language else SUPPORTED_LANGUAGES.keys()
    
    for lang in languages:
        lang_dir = USER_SCRIPTS_DIR / SUPPORTED_LANGUAGES[lang]['dir'] / category
        if not lang_dir.exists():
            continue
            
        for script_file in lang_dir.glob(f"*{SUPPORTED_LANGUAGES[lang]['ext']}"):
            if script_file.name == '.gitkeep':
                continue
            scripts.append(get_script_info(script_file))
    
    return scripts

def create_script(name: str, language: str, description: str = "") -> Path:
    """Create a new script from template."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    
    config = SUPPORTED_LANGUAGES[language]
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Generate filename
    script_name = f"{date_str}_{name}_{language}{config['ext']}"
    script_path = USER_SCRIPTS_DIR / config['dir'] / 'active' / script_name
    
    # Ensure directory exists
    script_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy from template
    template_path = USER_SCRIPTS_DIR / config['dir'] / 'templates' / f"basic_script{config['ext']}"
    
    if template_path.exists():
        shutil.copy2(template_path, script_path)
        
        # Update template placeholders
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace('[Brief description of what this script does]', description or f"Task: {name}")
        content = content.replace('[YYYY-MM-DD]', date_str)
        content = content.replace('[Creator name/identifier]', "User")
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        # Create minimal script if no template
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(f"# Task: {description or name}\n# Created: {date_str}\n\n# TODO: Implement your script here\n")
    
    return script_path

def archive_script(script_name: str, language: Optional[str] = None) -> bool:
    """Move a script from active to archived."""
    # Find the script
    scripts = list_scripts(language, 'active')
    target_script = None
    
    for script in scripts:
        if script_name in script['name']:
            target_script = script
            break
    
    if not target_script:
        return False
    
    source_path = Path(target_script['path'])
    
    # Determine target path
    lang = target_script['language']
    archived_dir = USER_SCRIPTS_DIR / SUPPORTED_LANGUAGES[lang]['dir'] / 'archived'
    archived_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = archived_dir / source_path.name
    
    # Move file
    shutil.move(source_path, target_path)
    return True

def restore_script(script_name: str, language: Optional[str] = None) -> bool:
    """Move a script from archived to active."""
    # Find the script
    scripts = list_scripts(language, 'archived')
    target_script = None
    
    for script in scripts:
        if script_name in script['name']:
            target_script = script
            break
    
    if not target_script:
        return False
    
    source_path = Path(target_script['path'])
    
    # Determine target path
    lang = target_script['language']
    active_dir = USER_SCRIPTS_DIR / SUPPORTED_LANGUAGES[lang]['dir'] / 'active'
    active_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = active_dir / source_path.name
    
    # Move file
    shutil.move(source_path, target_path)
    return True

def clean_logs(days: int = 7) -> int:
    """Clean old log files."""
    logs_dir = USER_SCRIPTS_DIR / 'shared' / 'logs'
    if not logs_dir.exists():
        return 0
    
    cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
    cleaned = 0
    
    for log_file in logs_dir.glob('*.log'):
        if log_file.stat().st_mtime < cutoff_time:
            log_file.unlink()
            cleaned += 1
    
    return cleaned

def main():
    parser = argparse.ArgumentParser(description="Manage user scripts for MCP Desktop Gateway")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List scripts')
    list_parser.add_argument('--language', '-l', choices=SUPPORTED_LANGUAGES.keys(), help='Filter by language')
    list_parser.add_argument('--category', '-c', choices=['active', 'archived'], default='active', help='Category to list')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new script from template')
    create_parser.add_argument('name', help='Script name (will be prefixed with date)')
    create_parser.add_argument('language', choices=SUPPORTED_LANGUAGES.keys(), help='Programming language')
    create_parser.add_argument('--description', '-d', help='Script description')
    
    # Archive command
    archive_parser = subparsers.add_parser('archive', help='Move script to archived')
    archive_parser.add_argument('script_name', help='Script name or pattern to match')
    archive_parser.add_argument('--language', '-l', choices=SUPPORTED_LANGUAGES.keys(), help='Filter by language')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Move script from archived to active')
    restore_parser.add_argument('script_name', help='Script name or pattern to match')
    restore_parser.add_argument('--language', '-l', choices=SUPPORTED_LANGUAGES.keys(), help='Filter by language')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean old logs and temporary files')
    clean_parser.add_argument('--days', '-d', type=int, default=7, help='Delete logs older than N days')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show script information')
    info_parser.add_argument('script_name', help='Script name or pattern to match')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'list':
            scripts = list_scripts(args.language, args.category)
            
            if not scripts:
                print(f"No {args.category} scripts found" + (f" for {args.language}" if args.language else ""))
                return 0
            
            print(f"{'=' * 60}")
            print(f"{args.category.title()} Scripts" + (f" ({args.language})" if args.language else ""))
            print(f"{'=' * 60}")
            
            for script in sorted(scripts, key=lambda x: x['modified'], reverse=True):
                print(f"\n📄 {script['name']}")
                print(f"   Language: {script['language'] or 'unknown'}")
                print(f"   Modified: {script['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Size: {script['size']} bytes")
                
                if script['description']:
                    print(f"   Description: {script['description']}")
                
                if args.verbose:
                    print(f"   Path: {script['path']}")
        
        elif args.command == 'create':
            script_path = create_script(args.name, args.language, args.description or "")
            print(f"✅ Created script: {script_path}")
            print(f"📝 Edit with: $EDITOR {script_path}")
            
        elif args.command == 'archive':
            if archive_script(args.script_name, args.language):
                print(f"✅ Archived script matching '{args.script_name}'")
            else:
                print(f"❌ No active script found matching '{args.script_name}'")
                return 1
                
        elif args.command == 'restore':
            if restore_script(args.script_name, args.language):
                print(f"✅ Restored script matching '{args.script_name}'")
            else:
                print(f"❌ No archived script found matching '{args.script_name}'")
                return 1
                
        elif args.command == 'clean':
            cleaned = clean_logs(args.days)
            print(f"🧹 Cleaned {cleaned} log files older than {args.days} days")
            
        elif args.command == 'info':
            scripts = list_scripts(None, 'active') + list_scripts(None, 'archived')
            target_script = None
            
            for script in scripts:
                if args.script_name in script['name']:
                    target_script = script
                    break
            
            if target_script:
                print(f"📄 Script Information")
                print(f"{'=' * 40}")
                print(f"Name: {target_script['name']}")
                print(f"Language: {target_script['language']}")
                print(f"Path: {target_script['path']}")
                print(f"Size: {target_script['size']} bytes")
                print(f"Modified: {target_script['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
                if target_script['description']:
                    print(f"Description: {target_script['description']}")
            else:
                print(f"❌ No script found matching '{args.script_name}'")
                return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())