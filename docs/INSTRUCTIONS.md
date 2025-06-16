# 🔧 Python Microservices - Development Instructions

**Version**: 1.0  
**Updated**: June 8, 2025

## 📌 1. Core Philosophy

These guidelines are for developers building robust, scalable, and maintainable microservices in Python. Our philosophy is rooted in Python's own principles:

- **Simplicity & Readability**: Prefer clear, straightforward code over complex, clever solutions. Readability counts.
- **Explicit is better than implicit**: Service contracts, configurations, and dependencies should be clearly defined.
- **Autonomy & Responsibility**: Each service should be independently deployable and managed by a team that owns it end-to-end.

> You are expected to follow all guidelines by default. Any deviation requires explicit justification and team consensus.

---

## 🧠 2. Core Principles

- **Build for Resilience**: Services can and will fail. Design for failure with patterns like retries, circuit breakers, and graceful degradation.
- **Single Responsibility Principle**: Each microservice should have one, well-defined responsibility.
- **Loose Coupling, High Cohesion**: Services should be loosely coupled (minimal dependencies on each other) while the code within a service should be highly cohesive (logically related).
- **Automation First**: Automate everything: testing, linting, building, deployment, and monitoring.
- **API as a Contract**: The API is the public contract of a service. It must be well-documented, versioned, and stable.

---

## 🛠️ 3. Development Environment

### Python Version
- This project uses **Python 3.11+**.
- Use a tool like `pyenv` to manage different Python versions on your local machine.

### Virtual Environments
- All Python development **MUST** happen inside a virtual environment to isolate project dependencies.
- Use the built-in `venv` module.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Activate it (Windows)
.\venv\Scripts\activate
```

### Dependency Management
- **Primary Tool**: `pip` with `requirements.txt` files.
- **Best Practice**: Use `pip-tools` to manage dependencies.
  - Define direct dependencies in a `requirements.in` file.
  - Compile it to a `requirements.txt` file with pinned, transitive dependencies.

```bash
# Install pip-tools
pip install pip-tools

# After creating requirements.in, compile it:
pip-compile requirements.in > requirements.txt

# Install dependencies from the locked file
pip install -r requirements.txt
```
- Each service should have its own `requirements.in` and `requirements.txt`.

---

## 🏗️ 4. Project & Service Structure

We recommend a monorepo structure for discoverability and simplified dependency management of shared libraries.

```
/
├── services/
│   ├── service-a/
│   │   ├── src/             # Service source code
│   │   ├── tests/           # Service tests
│   │   ├── Dockerfile
│   │   └── requirements.in
│   └── service-b/
│       └── ...
├── libs/
│   └── shared-library/      # Shared code (e.g., Pydantic models)
│       └── ...
├── docs/
├── scripts/
└── docker-compose.yml       # For local development orchestration
```

---

## ✅ 5. Code Quality & Style

We enforce a consistent code style to improve readability and reduce cognitive load. This is automated using pre-commit hooks.

### Tooling
- **Formatting**: `black` for uncompromising code formatting.
- **Linting & More**: `ruff` for extremely fast linting, import sorting, and enforcement of best practices.
- **Type Checking**: `mypy` for static type analysis.

### Pre-commit Hooks
- Configure these tools to run automatically before each commit using `pre-commit`.
- A sample `.pre-commit-config.yaml` can be found in project templates.

```bash
# Install pre-commit
pip install pre-commit

# Set up the git hooks
pre-commit install
```

---

## ⚙️ 6. Microservice Development

### Web Framework
- **Recommended**: `FastAPI` for its high performance, async support, and automatic OpenAPI documentation.
- **Alternative**: `Flask` for simpler services.

### Configuration
- Follow the **12-Factor App** methodology. Store configuration in environment variables.
- Use `.env` files for local development. **NEVER** commit `.env` files.
- **Recommended**: Use `pydantic-settings` to load environment variables into a typed, validated configuration object.

### Inter-Service Communication
- **Synchronous (Request/Reply)**: Use RESTful APIs over HTTP. Define your schema with Pydantic models, which FastAPI uses to generate OpenAPI specs.
- **Asynchronous (Event-Driven)**: For decoupling services, use a message broker like **RabbitMQ** or **Kafka**. This is preferred for non-blocking communication.
- **High-Performance RPC**: For internal, high-throughput communication, consider using **gRPC**.

### Logging
- Use **structured logging** (e.g., JSON format). This is critical for effective log analysis in a distributed system.
- The standard `logging` library can be configured for this, or use a library like `structlog`.

---

## 🧪 7. Testing Standards

- **Framework**: `pytest` is the standard for all Python testing.
- **Test Types**:
  - **Unit Tests**: Test individual functions and classes in isolation. Mock external dependencies.
  - **Integration Tests**: Test a service's interaction with other components like databases or external APIs. These can run against live test instances (e.g., a test database in Docker).
  - **Contract Tests**: Verify that a service adheres to the API contract expected by its consumers.
- **Code Coverage**: Aim for a minimum of **80%** test coverage. Use `pytest-cov`.
- **API Testing**: Use `httpx` within `pytest` to make requests to your service's API endpoints.

```bash
# Run tests for a service
pytest

# Run tests with coverage report
pytest --cov=src
```

---

## 🐳 8. Containerization

- All services **MUST** be containerized using `Docker`.
- Write a `Dockerfile` for each service.
- **Best Practices for Python Dockerfiles**:
  - Use multi-stage builds to keep production images small.
  - Run as a non-root user for security.
  - Optimize for layer caching.

### Local Orchestration
- Use `docker-compose.yml` to define and run all the project's services for local development. This makes it trivial to spin up the entire environment.

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# Stop services
docker-compose down
```

---

## 🚀 9. CI/CD

A CI/CD pipeline (e.g., using GitHub Actions) should be configured to automate the following workflow on every pull request and merge to `main`:

1. **Install Dependencies**.
2. **Run Code Quality Checks**: `black`, `ruff`, `mypy`.
3. **Run All Tests**: `pytest --cov`.
4. **Build Docker Images**: For each service.
5. (On merge to `main`) **Push Docker Images** to a container registry (e.g., Docker Hub, AWS ECR).
6. **Deploy** to the appropriate environment.

---

## 📘 10. Documentation

- **API Documentation**: If using FastAPI, OpenAPI documentation is automatically generated. Ensure it's clear by using good Pydantic model descriptions.
- **Code Documentation**: Use **Google-style** docstrings for all public modules, classes, and functions.
- **Architectural Documentation**: For significant new features or architectural changes, a **Design Document** is required. Store these in the `docs/design/` directory.

### Design Document Structure
```md
# Feature/System Name

## 1. Summary
What is this and why are we building it?

## 2. Problem & Scope
The pain point this addresses and explicit non-goals.

## 3. Technical Design
High-level architecture, data models, service interactions, and technology choices with rationale.

## 4. Implementation Plan
Phases, key milestones, and dependencies.

## 5. Open Questions
Unresolved issues to be addressed.
```

---

## 👁️ Final Note

Clear standards and thoughtful documentation create velocity. Write them like you're briefing a future teammate (or your future self).