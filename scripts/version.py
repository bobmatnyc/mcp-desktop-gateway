#!/usr/bin/env python3
"""
Semantic versioning helper for MCP Gateway
Manages version across Python and NPM
"""

import json
import re
import sys
import os
from pathlib import Path

VERSION_FILE = Path(__file__).parent.parent / "VERSION"
PACKAGE_JSON = Path(__file__).parent.parent / "package.json"
CONFIG_YAML = Path(__file__).parent.parent / "config" / "config.yaml"
INIT_FILE = Path(__file__).parent.parent / "src" / "__init__.py"

def get_current_version():
    """Get current version from VERSION file"""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "0.1.0"

def parse_version(version):
    """Parse semantic version string"""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    
    major, minor, patch, prerelease = match.groups()
    return {
        'major': int(major),
        'minor': int(minor),
        'patch': int(patch),
        'prerelease': prerelease,
        'full': version
    }

def bump_version(version, bump_type='patch'):
    """Bump version according to semver"""
    v = parse_version(version)
    
    if bump_type == 'major':
        return f"{v['major'] + 1}.0.0"
    elif bump_type == 'minor':
        return f"{v['major']}.{v['minor'] + 1}.0"
    elif bump_type == 'patch':
        return f"{v['major']}.{v['minor']}.{v['patch'] + 1}"
    elif bump_type == 'prerelease':
        if v['prerelease']:
            # Increment prerelease number
            pre_match = re.match(r'(.+)\.(\d+)', v['prerelease'])
            if pre_match:
                pre_name, pre_num = pre_match.groups()
                return f"{v['major']}.{v['minor']}.{v['patch']}-{pre_name}.{int(pre_num) + 1}"
            else:
                return f"{v['major']}.{v['minor']}.{v['patch']}-{v['prerelease']}.1"
        else:
            return f"{v['major']}.{v['minor']}.{v['patch']}-alpha.0"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")

def update_version_files(new_version):
    """Update version in all relevant files"""
    
    # Update VERSION file
    VERSION_FILE.write_text(new_version + '\n')
    print(f"✓ Updated VERSION file")
    
    # Update package.json
    if PACKAGE_JSON.exists():
        with open(PACKAGE_JSON, 'r') as f:
            data = json.load(f)
        data['version'] = new_version
        with open(PACKAGE_JSON, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        print(f"✓ Updated package.json")
    
    # Update config.yaml
    if CONFIG_YAML.exists():
        content = CONFIG_YAML.read_text()
        content = re.sub(
            r'version:\s*"[^"]*"',
            f'version: "{new_version}"',
            content
        )
        CONFIG_YAML.write_text(content)
        print(f"✓ Updated config.yaml")
    
    # Create/update __init__.py with version
    init_content = f'''"""MCP Gateway - Universal bridge for Claude Desktop"""

__version__ = "{new_version}"
__author__ = "MCP Gateway Team"
__license__ = "MIT"
'''
    if not INIT_FILE.parent.exists():
        INIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    INIT_FILE.write_text(init_content)
    print(f"✓ Updated src/__init__.py")

def create_git_tag(version, message=None):
    """Create git tag for release"""
    import subprocess
    
    if not message:
        message = f"Release v{version}"
    
    try:
        # Check if tag exists
        result = subprocess.run(
            ['git', 'tag', '-l', f'v{version}'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print(f"⚠️  Tag v{version} already exists")
            return False
        
        # Create tag
        subprocess.run(
            ['git', 'tag', '-a', f'v{version}', '-m', message],
            check=True
        )
        print(f"✓ Created git tag v{version}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create git tag: {e}")
        return False

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print(f"""
Semantic Versioning for MCP Gateway

Current version: {get_current_version()}

Usage:
  python scripts/version.py <command> [options]

Commands:
  show                Show current version
  bump <type>         Bump version (major|minor|patch|prerelease)
  set <version>       Set specific version
  tag [message]       Create git tag for current version

Examples:
  python scripts/version.py bump patch
  python scripts/version.py bump minor
  python scripts/version.py set 1.0.0
  python scripts/version.py tag "First stable release"
""")
        sys.exit(1)
    
    command = sys.argv[1]
    current = get_current_version()
    
    if command == 'show':
        print(f"Current version: {current}")
        
    elif command == 'bump':
        if len(sys.argv) < 3:
            print("Error: bump type required (major|minor|patch|prerelease)")
            sys.exit(1)
        
        bump_type = sys.argv[2]
        new_version = bump_version(current, bump_type)
        
        print(f"Bumping {bump_type}: {current} → {new_version}")
        update_version_files(new_version)
        
        print(f"\n✅ Version updated to {new_version}")
        print(f"\nNext steps:")
        print(f"  1. Commit changes: git add -A && git commit -m 'Bump version to {new_version}'")
        print(f"  2. Create tag: python scripts/version.py tag")
        print(f"  3. Push: git push && git push --tags")
        
    elif command == 'set':
        if len(sys.argv) < 3:
            print("Error: version required")
            sys.exit(1)
        
        new_version = sys.argv[2]
        try:
            parse_version(new_version)  # Validate
            update_version_files(new_version)
            print(f"\n✅ Version set to {new_version}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif command == 'tag':
        message = sys.argv[2] if len(sys.argv) > 2 else None
        if create_git_tag(current, message):
            print(f"\nNext step: git push --tags")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()