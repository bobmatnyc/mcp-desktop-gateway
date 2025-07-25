# MCP Desktop Gateway Development Makefile
# Modern Python 3.11+ development workflow with Ruff, Pyright, and security scanning

VERSION := $(shell cat VERSION 2>/dev/null || echo "1.0.0")
PYTHON := python3.11
VENV := venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
PYRIGHT := $(VENV)/bin/pyright

.PHONY: help setup dev test lint format type-check security audit clean install-dev test-npm run logs version use-local-code use-npm-package use-original backup-config restore-config config-dev config-npm config-status switch-dev switch-npm

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Environment Setup
setup: $(VENV) ## Set up modern Python 3.11+ development environment
	@echo "🚀 Setting up development environment with Python 3.11+ best practices..."
	$(PIP) install --upgrade pip wheel
	$(PIP) install -e ".[dev,test,security]"
	@echo "✅ Development environment ready!"

$(VENV):
	@echo "Creating Python 3.11+ virtual environment..."
	$(PYTHON) -m venv $(VENV)

dev: setup ## Alias for setup (backward compatibility)

install-dev: setup ## Install development dependencies
	@echo "📦 Installing development dependencies..."
	$(PIP) install -e ".[dev,test,security]"

# Code Quality and Formatting
lint: $(VENV) ## Run Ruff linter (fast, modern replacement for flake8, isort, etc.)
	@echo "🔍 Running Ruff linter..."
	$(RUFF) check src tests --fix

format: $(VENV) ## Format code with Ruff (replaces Black + isort)
	@echo "🎨 Formatting code with Ruff..."
	$(RUFF) format src tests

type-check: $(VENV) ## Run Pyright type checker
	@echo "🔍 Running Pyright type checker..."
	$(PYRIGHT) src

check: lint type-check ## Run all code quality checks
	@echo "✅ All code quality checks completed!"

# Security Scanning
security: $(VENV) ## Run security scans (pip-audit, bandit, safety)
	@echo "🔒 Running security scans..."
	$(VENV)/bin/pip-audit --desc
	$(VENV)/bin/bandit -r src -f json -o bandit-report.json || true
	$(VENV)/bin/safety check --json || true
	@echo "✅ Security scanning completed!"

audit: security ## Alias for security scanning

# Testing
test: $(VENV) ## Run tests with coverage using pytest
	@echo "🧪 Running tests with coverage..."
	$(PYTEST) -xvs --cov=src --cov-report=term-missing --cov-report=html

test-fast: $(VENV) ## Run tests in parallel (fast)
	@echo "⚡ Running tests in parallel..."
	$(PYTEST) -n auto --dist worksteal

test-unit: $(VENV) ## Run unit tests only
	@echo "🧪 Running unit tests..."
	$(PYTEST) tests/unit -v

test-integration: $(VENV) ## Run integration tests only
	@echo "🧪 Running integration tests..."
	$(PYTEST) tests/integration -v

# Development Workflow
run: $(VENV) ## Run gateway in development mode
	@echo "🏃 Running MCP Desktop Gateway (dev mode)..."
	@MCP_DEV_MODE=true $(VENV)/bin/python run_mcp_gateway.py

verify: test-mcp-current ## Verify all configured MCP services are working

run-simple: $(VENV) ## Run simple gateway
	@echo "🏃 Running Simple MCP Desktop Gateway..."
	@$(VENV)/bin/python run_mcp_gateway_simple.py

test-npm: ## Test NPM package locally
	@echo "Testing NPM package..."
	@bash test-package.sh

package: ## Build NPM package for distribution
	@echo "Building NPM package..."
	@npm pack
	@echo "Package created: mcp-desktop-gateway-*.tgz"

install-local: ## Install package locally via npm link
	@echo "Installing locally..."
	@npm link
	@echo "Run 'mcp-desktop-gateway' to test"

clean: ## Clean build artifacts
	@echo "Cleaning..."
	@rm -rf venv node_modules package-lock.json
	@rm -rf __pycache__ src/__pycache__ src/**/__pycache__
	@rm -rf .pytest_cache .coverage
	@rm -rf dist build *.egg-info
	@rm -f mcp-desktop-gateway-*.tgz
	@echo "Clean complete"

logs: ## Show Claude Desktop logs
	@echo "=== MCP Desktop Gateway Logs ==="
	@tail -n 50 ~/Library/Logs/Claude/mcp-server-mcp-desktop-gateway*.log

watch-logs: ## Watch Claude Desktop logs
	@echo "Watching MCP Desktop Gateway logs (Ctrl+C to stop)..."
	@tail -f ~/Library/Logs/Claude/mcp-server-mcp-desktop-gateway*.log

# Development workflow commands
edit-config: ## Edit gateway config
	@$$EDITOR config/config.yaml

edit-config-dev: ## Edit dev config
	@$$EDITOR config/config.dev.yaml

# MCP Service Testing
test-mcp-current: ## Test currently configured MCP services
	@echo "🧪 Testing currently configured MCP services..."
	@CONFIG_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.json"; \
	if [ -f "$$CONFIG_FILE" ]; then \
		./venv/bin/python scripts/test_mcp_service.py config "$$CONFIG_FILE"; \
	else \
		echo "❌ No Claude Desktop config found"; \
		exit 1; \
	fi

test-mcp-local: ## Test local MCP Desktop Gateway service
	@echo "🧪 Testing local MCP Desktop Gateway..."
	@echo "   Starting service for 3 seconds to verify it loads..."
	@( ./venv/bin/python run_mcp_gateway.py & PID=$$!; sleep 3; kill $$PID 2>/dev/null ) 2>&1 | grep -q "MCP Gateway Started" && \
		echo "   ✅ Local MCP Desktop Gateway starts successfully" || \
		echo "   ❌ Local MCP Desktop Gateway failed to start"

test-mcp-npm: ## Test NPM package MCP Desktop Gateway (must be installed)
	@echo "🧪 Testing NPM package MCP Desktop Gateway..."
	@which mcp-desktop-gateway > /dev/null || (echo "❌ mcp-desktop-gateway not found. Run 'npm install -g mcp-desktop-gateway' first"; exit 1)
	@./venv/bin/python scripts/test_mcp_service.py service "mcp-desktop-gateway (npm)" "mcp-desktop-gateway"

test: ## Run unit tests
	@echo "🧪 Running unit tests..."
	@./venv/bin/python scripts/run_tests.py

test-unit: ## Run only unit tests
	@echo "🧪 Running unit tests..."
	@./venv/bin/python scripts/run_tests.py tests/unit/ -v

test-integration: ## Run only integration tests
	@echo "🧪 Running integration tests..."
	@./venv/bin/python scripts/run_tests.py tests/integration/ -v

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	@./venv/bin/pip install coverage > /dev/null 2>&1 || true
	@PYTHONPATH=src ./venv/bin/python -m coverage run -m pytest tests/
	@./venv/bin/python -m coverage report
	@./venv/bin/python -m coverage html

# Configuration management - Three simple commands for Claude Desktop
use-local-code: ## Use MCP Desktop Gateway from local Python code (development)
	@echo "🔧 Testing local MCP Desktop Gateway before switching..."
	@$(MAKE) -s test-mcp-local || exit 1
	@CONFIG_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.json"; \
	ORIGINAL_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.original.json"; \
	if [ ! -f "$$ORIGINAL_FILE" ] && [ -f "$$CONFIG_FILE" ]; then \
		cp "$$CONFIG_FILE" "$$ORIGINAL_FILE"; \
		echo "📁 Saved original config for later restoration"; \
	fi; \
	./venv/bin/python scripts/merge_config.py "$$CONFIG_FILE" claude-configs/dev-config.json > "$$CONFIG_FILE.tmp" && \
	mv "$$CONFIG_FILE.tmp" "$$CONFIG_FILE"; \
	echo "✅ Now using MCP Desktop Gateway from local code at /Users/masa/Projects/mcp-desktop-gateway"; \
	echo "   (Replaced existing mcp gateway services, kept other services)"; \
	echo "🔄 Restart Claude Desktop to apply changes"; \
	echo ""; \
	echo "💡 Run 'make test-mcp-current' after restarting Claude to verify all services"

use-npm-package: ## Use MCP Desktop Gateway from NPM package
	@echo "🔧 Testing NPM MCP Desktop Gateway before switching..."
	@$(MAKE) -s test-mcp-npm || exit 1
	@CONFIG_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.json"; \
	ORIGINAL_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.original.json"; \
	if [ ! -f "$$ORIGINAL_FILE" ] && [ -f "$$CONFIG_FILE" ]; then \
		cp "$$CONFIG_FILE" "$$ORIGINAL_FILE"; \
		echo "📁 Saved original config for later restoration"; \
	fi; \
	echo '{"mcpServers":{"mcp-desktop-gateway":{"command":"mcp-desktop-gateway"}}}' > /tmp/mcp-desktop-gateway-npm-config.json; \
	./venv/bin/python scripts/merge_config.py "$$CONFIG_FILE" /tmp/mcp-desktop-gateway-npm-config.json > "$$CONFIG_FILE.tmp" && \
	mv "$$CONFIG_FILE.tmp" "$$CONFIG_FILE"; \
	rm -f /tmp/mcp-desktop-gateway-npm-config.json; \
	echo "✅ Now using MCP Desktop Gateway from NPM package"; \
	echo "   (Replaced existing mcp gateway services, kept other services)"; \
	echo "🔄 Restart Claude Desktop to apply changes"; \
	echo ""; \
	echo "💡 Run 'make test-mcp-current' after restarting Claude to verify all services"

use-original: ## Restore original Claude Desktop config
	@CONFIG_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.json"; \
	ORIGINAL_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.original.json"; \
	if [ -f "$$ORIGINAL_FILE" ]; then \
		cp "$$ORIGINAL_FILE" "$$CONFIG_FILE"; \
		echo "✅ Restored original Claude Desktop configuration"; \
		echo "🔄 Restart Claude Desktop to apply changes"; \
	else \
		echo "❌ No original config found"; \
		echo "💡 Your current config will be saved as 'original' next time you run use-local-code or use-npm-package"; \
	fi

# Legacy/advanced configuration commands
backup-config: ## Backup current Claude Desktop config
	@CONFIG_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.json"; \
	BACKUP_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.backup.json"; \
	if [ -f "$$CONFIG_FILE" ]; then \
		cp "$$CONFIG_FILE" "$$BACKUP_FILE"; \
		echo "✅ Backed up Claude Desktop config to claude_desktop_config.backup.json"; \
	else \
		echo "⚠️  No existing Claude Desktop config found at $$CONFIG_FILE"; \
	fi

restore-config: ## Restore backed up Claude Desktop config
	@CONFIG_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.json"; \
	BACKUP_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.backup.json"; \
	if [ -f "$$BACKUP_FILE" ]; then \
		cp "$$BACKUP_FILE" "$$CONFIG_FILE"; \
		echo "✅ Restored Claude Desktop config from backup"; \
		echo "🔄 Restart Claude Desktop to apply changes"; \
	else \
		echo "❌ No backup config found at claude_desktop_config.backup.json"; \
	fi

config-status: ## Show current Claude Desktop config
	@CONFIG_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.json"; \
	ORIGINAL_FILE="$$HOME/Library/Application Support/Claude/claude_desktop_config.original.json"; \
	echo "Current Claude Desktop configuration:"; \
	if [ -f "$$CONFIG_FILE" ]; then \
		cat "$$CONFIG_FILE" | ./venv/bin/python -m json.tool 2>/dev/null || cat "$$CONFIG_FILE"; \
	else \
		echo "No config file found at $$CONFIG_FILE"; \
	fi; \
	echo ""; \
	if [ -f "$$ORIGINAL_FILE" ]; then \
		echo "✅ Original config saved (use 'make use-original' to restore)"; \
	else \
		echo "⚠️  No original config saved yet"; \
	fi

# Legacy commands (kept for compatibility)
config-dev: use-local-code ## Switch to development config (deprecated: use use-local-code)
config-npm: use-npm-package ## Switch to NPM config (deprecated: use use-npm-package)
switch-dev: use-local-code ## Switch Claude to dev gateway (deprecated: use use-local-code)
switch-npm: use-npm-package ## Switch Claude to NPM gateway (deprecated: use use-npm-package)

# Version management
version: ## Show current version
	@echo "Current version: $(VERSION)"
	@./venv/bin/python scripts/version.py show

version-bump-patch: ## Bump patch version (0.1.0 -> 0.1.1)
	@./venv/bin/python scripts/version.py bump patch

version-bump-minor: ## Bump minor version (0.1.0 -> 0.2.0)
	@./venv/bin/python scripts/version.py bump minor

version-bump-major: ## Bump major version (0.1.0 -> 1.0.0)
	@./venv/bin/python scripts/version.py bump major

release: ## Create a release tag
	@./venv/bin/python scripts/version.py tag "Release v$(VERSION)"

publish: package ## Publish to NPM
	@echo "Publishing version $(VERSION) to NPM..."
	@npm publish --access public
	@echo "Published! Don't forget to push tags: git push --tags"