# MCP Gateway Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                           Claude Desktop                              │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    MCP Client (Built-in)                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 │ MCP Protocol
                                 │ (SSE/JSON-RPC)
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          MCP Gateway (Python)                         │
│                                                                       │
│  ┌─────────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │   MCP Server Core   │  │  Connector Hub  │  │  Router/Proxy  │  │
│  │  - Protocol Handler │  │  - Registry     │  │  - Load Balance│  │
│  │  - SSE Streaming    │  │  - Health Check │  │  - Auth Inject │  │
│  │  - Tool Registry    │  │  - Aggregation  │  │  - Namespacing │  │
│  └─────────────────────┘  └─────────────────┘  └────────────────┘  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                 Prompt Training System                        │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────────────┐    │  │
│  │  │ Feedback    │ │ Auto        │ │ LangChain Training   │    │  │
│  │  │ Collector   │ │ Trainer     │ │ - Few-shot Learning  │    │  │
│  │  │ - Ratings   │ │ - Monitor   │ │ - Reinforcement      │    │  │
│  │  │ - Errors    │ │ - Triggers  │ │ - Meta-prompt        │    │  │
│  │  │ - Success   │ │ - Deploy    │ │ - Adversarial        │    │  │
│  │  └─────────────┘ └─────────────┘ └──────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 │ HTTP REST API
                                 │
    ┌────────────────┬───────────┴───────────┬────────────────┐
    ▼                ▼                       ▼                ▼
┌─────────┐    ┌─────────┐            ┌─────────┐      ┌─────────┐
│Python   │    │Node.js  │            │Go       │      │Any      │
│Connector│    │Connector│            │Connector│      │Language │
├─────────┤    ├─────────┤            ├─────────┤      ├─────────┤
│- Flask  │    │- Express│            │- Gin    │      │- HTTP   │
│- Tools  │    │- Tools  │            │- Tools  │      │- Tools  │
│- Resources   │- Resources            │- Resources      │- Resources
│- Prompts│    │- Prompts│            │- Prompts│      │- Prompts│
└─────────┘    └─────────┘            └─────────┘      └─────────┘
     │              │                       │                 │
     ▼              ▼                       ▼                 ▼
┌─────────┐    ┌─────────┐            ┌─────────┐      ┌─────────┐
│Local    │    │Web APIs │            │Databases│      │System   │
│Services │    │(GitHub, │            │(MongoDB,│      │Commands │
│         │    │Slack...)│            │Redis...)│      │Scripts  │
└─────────┘    └─────────┘            └─────────┘      └─────────┘
```

## Component Details

### MCP Gateway Core

**Responsibilities:**
- Implement MCP server protocol
- Handle SSE connections from Claude
- Manage tool/resource/prompt registry
- Route requests to appropriate connectors

**Key Files:**
- `mcp_gateway.py` - Main gateway server
- `config/connectors.yaml` - Connector configuration

### Connector Hub

**Responsibilities:**
- Discover and register connectors
- Health check connectors
- Aggregate responses from multiple connectors
- Handle connector failures gracefully

**Features:**
- Dynamic connector registration
- Automatic retry with backoff
- Circuit breaker pattern
- Response caching

### Prompt Training System

**Responsibilities:**
- Automatically collect feedback from user interactions
- Monitor prompts for training opportunities
- Train improved versions using LangChain and ML
- Evaluate new versions and manage deployment
- Maintain version history and rollback capability

**Components:**
- **Feedback Collector**: Captures ratings, errors, success metrics, and suggestions
- **Automatic Trainer**: Monitors feedback patterns and triggers training
- **LangChain Integration**: Four training approaches (few-shot, reinforcement, meta-prompt, adversarial)
- **Prompt Manager**: Version control and deployment management
- **Evaluation Framework**: Automated testing with quality metrics

**Training Flow:**
1. Collect feedback during normal operations
2. Monitor for training triggers (error rates, ratings, volume)
3. Select optimal training approach based on feedback patterns
4. Train new version using LangChain
5. Evaluate against baseline with safety checks
6. Deploy if meets quality thresholds

### HTTP Connectors

**Responsibilities:**
- Implement specific service integrations
- Expose tools, resources, and prompts
- Handle authentication with target services
- Transform data between services and MCP

**API Contract:**
- `GET /info` - Connector metadata
- `GET /tools` - List available tools
- `POST /tools/{name}/execute` - Execute tool
- `GET /resources` - List resources
- `GET /resources/{uri}` - Read resource
- `GET /prompts` - List prompts
- `GET /prompts/{name}` - Get prompt

## Data Flow

### Tool Execution Flow

```
1. Claude Desktop: "Execute github_search with query='mcp'"
                                ↓
2. MCP Gateway: Receives MCP request
   - Parses tool name: "github_search"
   - Extracts connector: "github"
   - Finds connector URL from config
                                ↓
3. HTTP Request: POST http://localhost:8081/tools/search/execute
   Body: {"arguments": {"query": "mcp"}}
                                ↓
4. GitHub Connector: Executes search via GitHub API
                                ↓
5. HTTP Response: {"content": [{"type": "text", "text": "Results..."}]}
                                ↓
6. MCP Gateway: Formats as MCP response
                                ↓
7. Claude Desktop: Displays results
```

### Resource Access Flow

```
1. Claude requests: "github:file://README.md"
2. Gateway strips prefix, routes to GitHub connector
3. Connector fetches file from GitHub
4. Gateway returns content to Claude
```

## Security Considerations

### Authentication Layers

1. **MCP Level**: Optional bearer token for Claude→Gateway
2. **Connector Level**: Per-connector auth configuration
3. **Service Level**: Connector→Service authentication

### Best Practices

- Never expose service credentials to Claude
- Use environment variables for secrets
- Implement rate limiting per connector
- Log security events
- Validate all inputs

## Performance Optimization

### Caching Strategy
- Cache connector info (1 hour)
- Cache tool lists (5 minutes)
- Cache resource metadata (1 minute)
- No caching for tool execution

### Concurrency
- Async Python for gateway
- Parallel connector requests
- Connection pooling
- Request deduplication

### Monitoring
- Health checks every 30 seconds
- Metrics per connector
- Error rate tracking
- Response time monitoring

## Extension Points

### Custom Protocols
Beyond HTTP, the gateway can support:
- gRPC connectors
- WebSocket connectors
- Direct TCP connectors
- Native bindings

### Middleware
Add custom middleware for:
- Request transformation
- Response filtering
- Custom authentication
- Audit logging

### Plugins
Gateway supports plugins for:
- Custom routing logic
- Response aggregation
- Tool composition
- Workflow automation