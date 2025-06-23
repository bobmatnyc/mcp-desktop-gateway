# Changelog

All notable changes to MCP Gateway will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2025-06-23

### Added
- **Automatic Prompt Training System**: LangChain-powered continuous improvement system that learns from user feedback and errors
- **Smart Training Triggers**: Automatically triggers training based on error rates (>20%), low ratings (<0.6), feedback volume (50+ items), and user suggestions (3+)
- **Intelligent Approach Selection**: Four training approaches automatically selected based on feedback patterns:
  - Few-shot Learning for prompts with many successful examples
  - Reinforcement Learning for fixing low ratings and specific issues
  - Meta-prompt Optimization for incorporating user suggestions
  - Adversarial Training for handling edge cases and robustness
- **Continuous Monitoring**: Hourly checks of all prompts for training opportunities with configurable intervals and thresholds
- **Comprehensive Evaluation Framework**: Automated testing with quality metrics (coherence, relevance, safety) and A/B testing support
- **Training Management Tools**: Complete CLI interface for managing automatic training (status, start-auto, trigger, history)
- **User Feedback Tools**: `rate_response`, `suggest_improvement`, `report_issue`, `get_training_status`, `trigger_training`, `get_training_history`
- **Safe Deployment**: Thorough evaluation requirements with optional auto-deployment and rollback capability
- **Training History Tracking**: Detailed reports and history for all training sessions

### Enhanced
- **Shell Connector**: Updated prompts to emphasize script writing capabilities with clear Shell vs Terminal workflow
- **Terminal Connector**: Enhanced prompts to focus on script execution with visual feedback and tab management
- **Gateway Utils**: Updated complete services guide with new prompt training workflows and best practices
- **Documentation**: Enhanced all connector prompts with automatic training integration guidance

### Configuration
- **Auto-Training Config**: New `prompt_training/configs/auto_training.json` with comprehensive training settings
- **LangChain Dependencies**: Added langchain, langchain-openai, openai, tiktoken, faiss-cpu, and click to dependencies
- **Environment Variables**: Support for `OPENAI_API_KEY` environment variable for training features

### Technical Details
- **Training Pipeline**: Complete LangChain integration with multiple training strategies and evaluation metrics
- **Feedback Collection**: Automatic capture of user ratings, errors, success metrics, and improvement suggestions
- **Version Control**: Full prompt version management with deployment tracking and performance metrics
- **Integration Middleware**: Seamless integration with existing MCP Gateway connectors through middleware pattern
- **Safety Features**: 24-hour minimum training intervals, feedback requirements, evaluation thresholds, and manual review options

This release enables fully autonomous prompt improvement, making the MCP Desktop Gateway continuously learn and adapt based on real-world usage patterns without manual intervention.

## [1.0.0] - 2025-06-16

### Added
- **Complete MCP Desktop Gateway Implementation**: Production-ready universal bridge for Claude Desktop
- **Multi-Connector Architecture**: Modular system supporting shell, AppleScript, hello_world, and gateway_utils connectors
- **NPM Package Distribution**: Published as `@bobmatnyc/mcp-desktop-gateway` with automated setup
- **Comprehensive Test Suite**: 100+ unit tests covering core components and connectors (~60-70% coverage)
- **AppleScript Automation**: macOS-specific connectors for Safari, Contacts, Messages, and Finder
- **User Scripts Management**: Organized system for ad-hoc Python, JavaScript, Shell, and AppleScript code
- **Configuration Management**: YAML/JSON config loading with environment variable support
- **Development Tools**: Automated testing, version management, and CI-ready infrastructure
- **Security Features**: Command validation, input sanitization, and safe execution patterns
- **Documentation**: Comprehensive project documentation, API specs, and usage guides

### Changed
- **Version System**: Implemented semantic versioning (SemVer) across all components
- **Project Structure**: Organized codebase with proper separation of concerns
- **Configuration**: Unified configuration system with development/production environments
- **Testing**: From minimal integration tests to comprehensive unit test coverage

### Technical Details
- **Core Components**: ConnectorRegistry, BaseConnector, ConfigManager with full test coverage
- **MCP Protocol**: Complete implementation with tools, resources, and prompts support
- **REST API**: Optional HTTP interface for connector integration
- **CLI Interface**: Node.js wrapper for Python-based gateway with proper stdio handling
- **Build System**: Makefile automation for testing, deployment, and version management

## [0.1.0] - 2024-01-11

### Added
- Initial release of MCP Gateway
- Built-in connectors: Shell, AppleScript, Hello World, Gateway Utils
- NPM package distribution with automatic Python setup
- Support for external HTTP connectors
- Comprehensive documentation and examples
- Development workflow with Makefile
- Semantic versioning support

### Features
- 15 built-in tools for system automation
- 10 resources for system information
- 8 prompts for guided assistance
- Security features: command filtering, timeouts
- Cross-platform support (with platform-specific features)
- Automatic bytecode compilation for performance

## [0.1.0] - 2024-01-11

### Added
- Initial alpha release
- Core MCP protocol implementation
- Basic connector architecture
- Claude Desktop integration

---

## Version History Format

### Version Numbering
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)
- **PRERELEASE**: Alpha/Beta versions (x.y.z-alpha.n)

### Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes