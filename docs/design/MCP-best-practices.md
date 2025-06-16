# Comprehensive MCP Tools Development Guide

## Introduction

The Model Context Protocol (MCP) is an open standard developed by Anthropic that enables AI assistants to connect with external data sources and tools. This guide provides comprehensive instructions for MCP tools development, covering coding best practices, configuration schemas, and Claude Code integration based on current 2024-2025 practices.

## Part 1: Coding Best Practices for MCP Tools

### Development Architecture and Patterns

MCP follows a **client-server architecture** with three core components:
- **MCP Hosts**: Applications like Claude Desktop, IDEs, or AI tools
- **MCP Clients**: Protocol clients maintaining 1:1 connections with servers  
- **MCP Servers**: Lightweight programs exposing capabilities through MCP

**Key Architectural Patterns:**

1. **Stateless Design** (Recommended)
   ```typescript
   // Example: Stateless server implementation
   const server = new McpServer({
     name: "stateless-server",
     version: "1.0.0"
   });
   
   // Each request is independent
   server.tool("calculate", schema, async (params) => {
     return { content: [{ type: "text", text: `Result: ${params.a + params.b}` }] };
   });
   ```

2. **Transport Layer Selection**
   - **stdio**: Best for local development and desktop applications
   - **HTTP Streaming**: Optimal for remote servers and production deployments
   - **SSE**: Being phased out, avoid for new projects

### Code Organization Best Practices

**TypeScript Project Structure:**
```
mcp-server/
├── src/
│   ├── index.ts          # Main server entry point
│   ├── tools/            # Tool implementations
│   ├── resources/        # Resource handlers
│   ├── prompts/          # Prompt templates
│   ├── auth/             # Authentication middleware
│   ├── utils/            # Helper functions
│   └── types/            # Type definitions
├── tests/
│   ├── unit/
│   └── integration/
├── package.json
├── tsconfig.json
└── README.md
```

**Python Project Structure:**
```
mcp_server/
├── src/
│   ├── __init__.py
│   ├── server.py         # Main server
│   ├── tools/            # Tool modules
│   ├── resources/        # Resource handlers
│   ├── auth/             # Authentication
│   └── utils/            # Utilities
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Error Handling and Logging

**Hierarchical Error Classification:**
```typescript
enum MCPErrorType {
  PROTOCOL_ERROR = -32000,
  AUTHENTICATION_ERROR = -32001,
  AUTHORIZATION_ERROR = -32002,
  RESOURCE_NOT_FOUND = -32003,
  TOOL_EXECUTION_ERROR = -32004
}

class MCPError extends Error {
  constructor(
    public code: MCPErrorType,
    message: string,
    public data?: any
  ) {
    super(message);
  }
}
```

**Structured Logging Pattern:**
```typescript
import winston from 'winston';

const logger = winston.createLogger({
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

// Usage
logger.info('Tool executed', {
  toolName: 'calculate',
  parameters: { a: 5, b: 3 },
  executionTime: 23,
  success: true
});
```

### Performance Optimization

**Multi-Level Caching:**
```typescript
class MCPCache {
  private cache = new Map<string, { data: any; expires: number }>();
  
  set(key: string, data: any, ttlMs: number) {
    this.cache.set(key, {
      data,
      expires: Date.now() + ttlMs
    });
  }
  
  get(key: string) {
    const entry = this.cache.get(key);
    if (!entry || Date.now() > entry.expires) {
      this.cache.delete(key);
      return null;
    }
    return entry.data;
  }
}
```

**Connection Pooling (Python):**
```python
import asyncpg
from asyncpg import create_pool

class DatabaseManager:
    def __init__(self, dsn: str):
        self.pool = None
        self.dsn = dsn
    
    async def initialize(self):
        self.pool = await create_pool(
            self.dsn,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
    
    async def execute_query(self, query: str):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query)
```

### Testing Methodologies

**TypeScript Testing with Jest:**
```typescript
// __tests__/calculator.test.ts
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

describe('Calculator Tools', () => {
  let server: McpServer;
  
  beforeEach(() => {
    server = new McpServer({
      name: "test-server",
      version: "1.0.0"
    });
  });
  
  test('add tool should return correct sum', async () => {
    const result = await server.callTool('add', { a: 5, b: 3 });
    expect(result.content).toBe(8);
  });
  
  test('should handle invalid input gracefully', async () => {
    await expect(
      server.callTool('add', { a: 'invalid', b: 3 })
    ).rejects.toThrow('Invalid input parameters');
  });
});
```

**Integration Testing with MCP Inspector:**
```bash
# Test server interactively
npx @modelcontextprotocol/inspector node build/index.js

# Test with specific arguments
npx @modelcontextprotocol/inspector uvx mcp-server-git --repository ~/code/repo.git
```

### Security Best Practices

**Token-Based Authentication:**
```typescript
class AuthMiddleware {
  constructor(private validTokens: Set<string>) {}
  
  async authenticate(request: Request): Promise<boolean> {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return false;
    }
    
    const token = authHeader.substring(7);
    return this.validTokens.has(token);
  }
}
```

**Input Validation:**
```python
from pydantic import BaseModel, validator

class ToolInput(BaseModel):
    query: str
    limit: int = 10
    
    @validator('query')
    def validate_query(cls, v):
        if len(v) > 1000:
            raise ValueError('Query too long')
        return v.strip()
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Limit must be between 1 and 100')
        return v
```

### Platform-Specific Best Practices

**TypeScript/Next.js Integration:**
```typescript
// app/api/mcp/route.ts
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamable-http.js';

export async function POST(request: Request) {
  const server = new McpServer({
    name: "nextjs-mcp-server",
    version: "1.0.0"
  });
  
  // Configure tools, resources, and prompts
  await setupServerCapabilities(server);
  
  const transport = new StreamableHTTPServerTransport();
  await server.connect(transport);
  
  return await transport.handleRequest(request);
}
```

**Python FastMCP Framework:**
```python
from fastmcp import FastMCP
from pydantic import BaseModel

app = FastMCP("Python MCP Server")

class AddRequest(BaseModel):
    a: float
    b: float

@app.tool()
async def add_numbers(request: AddRequest) -> float:
    """Add two numbers together."""
    return request.a + request.b

if __name__ == "__main__":
    app.run()
```

## Part 2: Configuration Schemas for MCP Tools

### Core Configuration Structure

MCP servers are configured using JSON files with the following structure:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "string",
      "args": ["string"],
      "env": {
        "ENV_VAR": "value"
      },
      "timeout": 30000,
      "type": "stdio" | "sse" | "http"
    }
  }
}
```

### Configuration File Locations

Different clients support various configuration file locations:

| Client | Configuration Path |
|--------|-------------------|
| VS Code | `.vscode/mcp.json` (workspace) |
| Cursor | `~/.cursor/mcp.json` (global), `.cursor/mcp.json` (project) |
| Claude Desktop | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json` |
| | Windows: `%APPDATA%\Claude\claude_desktop_config.json` |
| Amazon Q | `~/.aws/amazonq/mcp.json` (global), `.amazonq/mcp.json` (workspace) |

### Tool Schema Definition

```json
{
  "name": "tool_name",
  "description": "Tool description",
  "inputSchema": {
    "type": "object",
    "properties": {
      "parameter_name": {
        "type": "string",
        "description": "Parameter description"
      }
    },
    "required": ["parameter_name"]
  },
  "annotations": {
    "title": "Human-readable title",
    "readOnlyHint": true,
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false
  }
}
```

### Enhanced Configuration with Inputs

```json
{
  "inputs": [
    {
      "id": "api_key",
      "description": "API key for service",
      "type": "promptString",
      "password": true
    }
  ],
  "servers": {
    "my-server": {
      "type": "stdio",
      "command": "node",
      "args": ["server.js"],
      "env": {
        "API_KEY": "${input:api_key}"
      }
    }
  }
}
```

### Error Response Schema

```json
{
  "jsonrpc": "2.0",
  "id": "request_id",
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "details": "Additional error context"
    }
  }
}
```

**Standard Error Codes:**

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Invalid Request object |
| -32601 | Method not found | Method does not exist |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Internal JSON-RPC error |

### Protocol Version Management

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "clientInfo": {
      "name": "Claude Desktop",
      "version": "1.0.0"
    }
  }
}
```

### Real-World Configuration Examples

**File System Server:**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/workspace"],
      "timeout": 10000
    }
  }
}
```

**Database Server with Authentication:**
```json
{
  "inputs": [
    {
      "id": "db_password",
      "description": "Database password",
      "type": "promptString",
      "password": true
    }
  ],
  "mcpServers": {
    "postgres": {
      "command": "node",
      "args": ["./dist/index.js"],
      "env": {
        "DATABASE_URL": "postgresql://user:${input:db_password}@localhost/mydb"
      }
    }
  }
}
```

## Part 3: Claude Code for Building MCP Tools

### Claude Code Architecture

Claude Code functions as both an MCP client and server:
- **As MCP Client**: Connects to external MCP servers to access their tools
- **As MCP Server**: Exposes capabilities via `claude mcp serve`

### Adding MCP Servers with Claude Code

**Basic Commands:**
```bash
# Add a local server
claude mcp add <server-name> <command> [args...]

# Add with environment variables
claude mcp add my-server -s user -e API_KEY=123 -- /path/to/server arg1 arg2

# Add SSE server
claude mcp add --transport sse sse-server https://example.com/sse-endpoint
```

**Configuration Scopes:**

1. **Local Scope** (Default)
   ```bash
   claude mcp add my-private-server /path/to/server
   ```
   - Available only in current project directory

2. **User Scope**
   ```bash
   claude mcp add my-user-server -s user /path/to/server
   ```
   - Available across all projects for your user

3. **Project Scope**
   ```bash
   claude mcp add team-server -s project /path/to/server
   ```
   - Creates/updates `.mcp.json` for team sharing

### Management Commands

```bash
# List all configured servers
claude mcp list

# Get server details
claude mcp get my-server

# Remove a server
claude mcp remove my-server

# Reset project choices for approval
claude mcp reset-project-choices
```

### Code Generation with Custom Commands

Create reusable templates in `.claude/commands/`:

```bash
# Create project-level command
echo "Analyze the performance of this code and suggest three specific optimizations:" > .claude/commands/optimize.md

# Create user-level command  
echo "Review this code for security vulnerabilities, focusing on:" > ~/.claude/commands/security-review.md
```

**Parameterized Commands:**
```markdown
<!-- .claude/commands/fix-issue.md -->
Find and fix issue #$ARGUMENTS. Follow these steps:
1. Understand the issue described in the ticket
2. Locate the relevant code in our codebase  
3. Implement a solution that addresses the root cause
4. Add appropriate tests
5. Prepare a concise PR description
```

### Debugging and Testing

**Debug Mode:**
```bash
# Launch with MCP debugging enabled
claude --mcp-debug

# Debug specific MCP configuration issues
MCP_CLAUDE_DEBUG=true claude
```

**Testing Workflow:**
```bash
# Test server registration
claude mcp add test-server -- node dist/server.js

# Verify tools are available
claude -p "What tools do you have available?"

# Test specific functionality
claude -p "Use the example_tool with parameter 'test'"
```

### CI/CD Integration

**GitHub Actions Example:**
```yaml
# .github/workflows/claude-code.yml
name: Claude Code Automation
on: [push, pull_request]

jobs:
  code-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Claude Code
        run: npm install -g @anthropic-ai/claude-code
      - name: Run automated review
        run: claude -p "Review this PR for code quality" --output-format json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Popular MCP Server Examples

```bash
# Filesystem access
claude mcp add filesystem -s user -- npx -y @modelcontextprotocol/server-filesystem ~/Projects

# Web automation  
claude mcp add puppeteer -s user -- npx -y @modelcontextprotocol/server-puppeteer

# Git operations
claude mcp add git -s user -- npx -y @modelcontextprotocol/server-git

# Sequential thinking
claude mcp add thinking -s user -- npx -y @modelcontextprotocol/server-sequential-thinking

# GitHub integration with API key
claude mcp add github -s user -e GITHUB_TOKEN=your_token -- npx -y @modelcontextprotocol/server-github
```

### Development Workflow Best Practices

```bash
# 1. Clear context frequently
/clear

# 2. Use Git worktrees for parallel development
git worktree add ../feature-branch -b new-feature
cd ../feature-branch && claude

# 3. Resume conversations efficiently  
claude --continue
claude --resume  # for conversation picker

# 4. Organize MCP servers by scope
# Project-specific: database connections, build tools
# User-level: personal utilities, development helpers  
# Global: widely applicable tools
```

## Complete Implementation Example

### TypeScript MCP Server

```typescript
// src/index.ts
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema
} from '@modelcontextprotocol/sdk/types.js';

const server = new McpServer({
  name: "comprehensive-mcp-server",
  version: "1.0.0"
});

// Tool implementations
const tools = {
  async calculateSum(a: number, b: number): Promise<number> {
    return a + b;
  },
  
  async fetchWeather(location: string): Promise<string> {
    // Simulate API call
    return `Weather in ${location}: 72°F, sunny`;
  }
};

// Set up tool handlers
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "calculate_sum",
      description: "Add two numbers",
      inputSchema: {
        type: "object",
        properties: {
          a: { type: "number" },
          b: { type: "number" }
        },
        required: ["a", "b"]
      }
    },
    {
      name: "fetch_weather",
      description: "Get weather for a location",
      inputSchema: {
        type: "object",
        properties: {
          location: { type: "string" }
        },
        required: ["location"]
      }
    }
  ]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  
  switch (name) {
    case "calculate_sum":
      const result = await tools.calculateSum(args.a, args.b);
      return {
        content: [{ type: "text", text: `Result: ${result}` }]
      };
    
    case "fetch_weather":
      const weather = await tools.fetchWeather(args.location);
      return {
        content: [{ type: "text", text: weather }]
      };
    
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
});

// Resource handlers
server.setRequestHandler(ListResourcesRequestSchema, async () => ({
  resources: [
    {
      uri: "config://settings",
      name: "Server Settings",
      description: "Current server configuration"
    }
  ]
}));

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("MCP server running on stdio");
}

main().catch(console.error);
```

### Python MCP Server

```python
# server.py
import asyncio
import logging
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, CallToolResult

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server
server = FastMCP("Python MCP Server")

@server.tool()
async def calculate_sum(a: float, b: float) -> float:
    """Add two numbers together."""
    logger.info(f"Calculating sum of {a} and {b}")
    return a + b

@server.tool()
async def fetch_weather(location: str) -> str:
    """Get weather information for a location."""
    logger.info(f"Fetching weather for {location}")
    # Simulate API call
    await asyncio.sleep(0.1)
    return f"Weather in {location}: 72°F, sunny"

@server.resource("config://settings")
async def get_server_settings() -> str:
    """Get current server configuration."""
    return "Server is running in production mode"

# Error handling
@server.error_handler
async def handle_error(error: Exception) -> Dict[str, Any]:
    logger.error(f"Error occurred: {error}")
    return {
        "error": "Internal server error",
        "message": str(error)
    }

if __name__ == "__main__":
    # Run the server
    server.run()
```

## Key Takeaways

### For Beginners
1. Start with the official MCP Inspector for testing
2. Use FastMCP (Python) or template patterns (TypeScript) for rapid prototyping
3. Focus on simple, stateless tools initially
4. Implement proper error handling from the start

### For Advanced Developers
1. Implement comprehensive testing strategies including unit, integration, and E2E tests
2. Use multi-level caching for performance optimization
3. Implement proper authentication and authorization patterns
4. Design for scalability with connection pooling and async patterns
5. Monitor performance metrics and implement proper logging

### Production Readiness Checklist
- [ ] Comprehensive error handling and logging
- [ ] Authentication and authorization
- [ ] Rate limiting and abuse protection
- [ ] Performance monitoring and metrics
- [ ] Automated testing pipeline
- [ ] Security scanning and vulnerability assessment
- [ ] Deployment automation and rollback procedures
- [ ] Documentation and API specifications

This comprehensive guide provides the foundation for building robust, scalable, and secure MCP tools that integrate seamlessly with modern AI applications and workflows. The MCP ecosystem continues to evolve rapidly, with new capabilities and community contributions emerging regularly.