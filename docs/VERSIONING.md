# Semantic Versioning Strategy

MCP Desktop Gateway follows [Semantic Versioning (SemVer)](https://semver.org/) with the format `MAJOR.MINOR.PATCH`.

## Version Format: X.Y.Z

- **MAJOR** (`X`): Breaking changes that require user action
- **MINOR** (`Y`): New features that are backwards compatible
- **PATCH** (`Z`): Bug fixes and minor improvements

## Current Version: 1.0.0

The project has reached **stable release status** as of version 1.0.0.

## Version Management

### Automated Versioning

Use the built-in version management script:

```bash
# Check current version
python scripts/version.py show

# Set specific version
python scripts/version.py set 1.2.3

# Bump version types
python scripts/version.py bump patch    # 1.0.0 → 1.0.1
python scripts/version.py bump minor    # 1.0.0 → 1.1.0
python scripts/version.py bump major    # 1.0.0 → 2.0.0

# Create pre-release
python scripts/version.py bump prerelease  # 1.0.0 → 1.0.1-alpha.1

# Create git tag
python scripts/version.py tag
```

### Makefile Commands

```bash
# Quick version bumps with automatic testing
make version-bump-patch  # Runs tests, bumps patch, creates tag
make version-bump-minor  # Runs tests, bumps minor, creates tag
make version-bump-major  # Runs tests, bumps major, creates tag

# Show current version
make version-show
```

## Files Updated by Version Changes

The version management system automatically updates:

1. **`VERSION`** - Canonical version source
2. **`package.json`** - NPM package version
3. **`pyproject.toml`** - Python package version  
4. **`setup.py`** - Fallback Python package version
5. **`src/__init__.py`** - Python module version
6. **`config/config.yaml`** - Server configuration version

## Version Bump Guidelines

### MAJOR Version (X.0.0)

Increment for **breaking changes** that require user action:

- Removing or renaming public APIs
- Changing configuration file format
- Removing connectors or tools
- Major architecture changes
- Incompatible dependency updates

**Examples:**
- `1.5.2 → 2.0.0`: Removed legacy shell connector
- `2.1.0 → 3.0.0`: New configuration format required

### MINOR Version (X.Y.0)

Increment for **new features** that are backwards compatible:

- Adding new connectors
- Adding new tools to existing connectors
- New configuration options (with defaults)
- Performance improvements
- Enhanced functionality

**Examples:**
- `1.2.1 → 1.3.0`: Added Calendar connector
- `1.3.0 → 1.4.0`: Added batch execution feature

### PATCH Version (X.Y.Z)

Increment for **bug fixes** and minor improvements:

- Bug fixes
- Security patches
- Documentation updates
- Code refactoring (no API changes)
- Dependency updates (compatible)

**Examples:**
- `1.3.0 → 1.3.1`: Fixed shell command timeout issue
- `1.3.1 → 1.3.2`: Updated dependencies for security

## Pre-release Versions

For development and testing:

```bash
# Alpha releases (early development)
1.4.0-alpha.1
1.4.0-alpha.2

# Beta releases (feature complete, testing)
1.4.0-beta.1
1.4.0-beta.2

# Release candidates (ready for production)
1.4.0-rc.1
1.4.0-rc.2
```

## Git Tagging Strategy

### Tag Format

- **Release tags**: `v1.0.0`, `v1.2.3`
- **Pre-release tags**: `v1.0.0-alpha.1`, `v1.0.0-beta.2`

### Tag Creation

```bash
# Automatic tagging (recommended)
python scripts/version.py tag

# Manual tagging
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Release Process

### 1. Development Phase
```bash
# Work on features in feature branches
git checkout -b feature/new-connector
# ... develop feature
git commit -m "feat: add new database connector"
```

### 2. Pre-release Testing
```bash
# Create pre-release for testing
python scripts/version.py bump prerelease
# Test thoroughly
make test
make test-integration
```

### 3. Release Preparation
```bash
# Ensure all tests pass
make test

# Update changelog
vim CHANGELOG.md

# Bump version (automatically runs tests)
make version-bump-minor  # or patch/major

# Push release
git push origin main --tags
```

### 4. NPM Package Release
```bash
# Build and publish NPM package
npm run build
npm publish --access public
```

## Changelog Maintenance

Update `CHANGELOG.md` for each release following [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [1.2.0] - 2025-06-16

### Added
- New database connector with PostgreSQL support
- Batch execution capability for shell commands

### Changed
- Improved error handling in AppleScript connector
- Enhanced configuration validation

### Fixed
- Shell command timeout issue (#123)
- Memory leak in resource management (#124)

### Security
- Updated dependencies for CVE-2024-12345
```

## Branch Strategy

### Main Branches
- **`main`**: Stable release branch (protected)
- **`develop`**: Integration branch for features

### Feature Branches
- **`feature/*`**: New features (minor version bump)
- **`hotfix/*`**: Critical fixes (patch version bump)
- **`release/*`**: Release preparation (version bump)

### Version Bump Triggers

Automatic version bumping based on commit messages:

- **Major**: `BREAKING CHANGE:` in commit message
- **Minor**: `feat:` prefix
- **Patch**: `fix:` prefix

## Compatibility Matrix

| Version Range | Node.js | Python | MCP Protocol |
|---------------|---------|--------|--------------|
| 1.0.x         | ≥18.0   | ≥3.8   | 2024-11-05   |
| 1.1.x         | ≥18.0   | ≥3.8   | 2024-11-05   |
| 2.0.x         | ≥20.0   | ≥3.9   | 2025-01-01   |

## Version History

| Version | Date       | Type    | Major Changes |
|---------|------------|---------|---------------|
| 1.0.0   | 2025-06-16 | Stable  | Initial stable release |
| 0.1.0   | 2024-01-11 | Alpha   | Initial implementation |

## Best Practices

### For Contributors

1. **Follow conventional commits**: Use `feat:`, `fix:`, `docs:` prefixes
2. **Test before version bumps**: Always run `make test` first
3. **Update changelog**: Document all user-facing changes
4. **Tag releases**: Use `python scripts/version.py tag` for consistency

### For Maintainers

1. **Review breaking changes**: Carefully consider major version bumps
2. **Coordinate releases**: Ensure all stakeholders are informed
3. **Maintain compatibility**: Follow deprecation policies
4. **Security updates**: Prioritize security patches

## Tools and Scripts

- **`scripts/version.py`**: Main version management script
- **`Makefile`**: Automated version bump targets
- **`.semverrc`**: Semantic versioning configuration
- **GitHub Actions**: Automated release workflow (if configured)

## Support Policy

- **Current Major Version**: Full support with new features and fixes
- **Previous Major Version**: Security and critical bug fixes only
- **Older Versions**: Community support only

For questions about versioning strategy, see [Contributing Guidelines](CONTRIBUTING.md) or open an issue.