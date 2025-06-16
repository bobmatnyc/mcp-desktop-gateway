# MCP Desktop Gateway Development Makefile
VERSION := $(shell cat VERSION 2>/dev/null || echo "0.1.0")

.PHONY: help dev test package clean install-dev test-npm run logs version use-local-code use-npm-package use-original backup-config restore-config config-dev config-npm config-status switch-dev switch-npm

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev: ## Set up development environment
	@echo "Setting up development environment..."
	@bash dev-setup.sh

run: ## Run gateway in development mode
	@echo "Running MCP Desktop Gateway (dev mode)..."
	@MCP_DEV_MODE=true ./venv/bin/python run_mcp_gateway.py

verify: test-mcp-current ## Verify all configured MCP services are working

run-simple: ## Run simple gateway
	@echo "Running Simple MCP Desktop Gateway..."
	@./venv/bin/python run_mcp_gateway_simple.py

test: ## Run Python tests
	@echo "Running tests..."
	@./venv/bin/python -m pytest tests/ -v

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
	@( ./venv/bin/python run_mcp_gateway.py & PID=$$!; sleep 3; kill $$PID 2>/dev/null ) 2>&1 | grep -q "MCP Desktop Gateway Started" && \
		echo "   ✅ Local MCP Desktop Gateway starts successfully" || \
		echo "   ❌ Local MCP Desktop Gateway failed to start"

test-mcp-npm: ## Test NPM package MCP Desktop Gateway (must be installed)
	@echo "🧪 Testing NPM package MCP Desktop Gateway..."
	@which mcp-desktop-gateway > /dev/null || (echo "❌ mcp-desktop-gateway not found. Run 'npm install -g mcp-desktop-gateway' first"; exit 1)
	@./venv/bin/python scripts/test_mcp_service.py service "mcp-desktop-gateway (npm)" "mcp-desktop-gateway"

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