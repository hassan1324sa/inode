# Fluxa Master Roadmap - Remaining Phases (8 to 13)

This document outlines the strategic roadmap and technical architecture for the remaining phases of the Fluxa Agentic Operating System.

---

## Phase 8: Agent Kernel, Planner, Memory & Knowledge Layer
Transforms Fluxa from a structured workflow executor into a reasoning Agent Kernel.

### 8.1 Agent Kernel & Reasoning Loop
* **AgentKernel Abstraction**: Coordinates Planner, PlanExecutor, ToolExecutor, Memory, and Knowledge components. The execution engine loop remains clean and decoupled from LLM logic.
* **Planning Policy**: Swappable planner engines (e.g., `SequentialPlanner`, `ReActPlanner`, `PlanAndSolvePlanner`, `TreeOfThoughtPlanner`) that generate an abstract `Plan` processed by a separate `PlanExecutor`. Behavior is guided by a `PlanningPolicy` (parameters: `max_iterations`, `allow_parallel`, `require_approval`, `max_cost`, `preferred_tools`).
* **Tool Capability Negotiation**: Tools execute through standard stages: **Discover**, **Validate**, **Negotiate**, and **Execute** for dynamic tool selection.
* **Tool Registry**: Common tool interface mapping multiple categories:
  * **Native Tools**: Raw Python code extensions.
  * **Node-backed Tools**: Existing Fluxa workflow nodes exposed as tool schemas.
  * **MCP Tools**: Dynamic tools exposed via Model Context Protocol.
  * **Remote Tools**: REST/GraphQL endpoints, Browser APIs, and Computer Use.

### 8.2 Memory vs. Knowledge Layer
* **Memory Layer**:
  * **Working Memory**: In-flight reasoning loop traces.
  * **Session Memory**: Conversational contexts and state variables.
  * **Episodic Memory**: Semantic embeddings of past session runs.
  * **Semantic Memory**: Persistent associative concepts (swappable memory providers: `ChromaMemory`, `QdrantMemory`, `PostgresMemory`, `RedisMemory`).
* **Knowledge Layer**: Separated document store, embeddings, chunking pipeline, semantic search retrieval, and source citation engine.
* **Skills as Packages**: Reusable package structures containing a manifest, tool schemas, templates, and optional memory rules.
* **Event-Driven Agent Communication**: Agents communicate strictly via the task dispatcher and `ExecutionEventBus`.

### 8.3 Unified Capability System
* An abstraction layer where **Nodes**, **Tools**, **Skills**, **Providers**, and **Triggers** map to generic **Capabilities**. Planners can dynamically query: *"Who can satisfy capability X?"* rather than search for hardcoded names.

### 8.4 AI Governance & Evaluation
* Centralized components: **Prompt Templates**, **Prompt Registry**, **Model Routing**, **Fallback Chain**, **Cost Budget**, and **Safety Policies**.
* **Evaluation Layer**: Intercepts outputs for validations: Prompt -> Model -> Output -> Evaluation (LLM-as-a-Judge, Schema parsing, JSON validation) -> Accept/Retry/Fallback.

---

## Phase 9: Dashboard, API & Visual Live Builder
Building user interfaces for visual building and runtime monitoring.

### 9.1 Backend API & Visual Builder
* **FastAPI Backend Endpoints**: Full API coverage for compiling, triggering, and managing workflows and agent sessions.
* **Visual Live Builder Bindings**: Dynamically generates visual UI blocks matching registry schemas.

### 9.2 Event-Driven Execution Stream
* **Execution Event Stream -> Projection -> Dashboard**: Real-time event streams capturing running executions.
* **Execution Timeline**: Rich visual timeline for debugging: **Replay**, **Diff**, **Step Inspection**, and **Variable History**.

---

## Phase 10: Multi-Tenant Architecture & Enterprise Security
Adding security and cost tracking.

### Key Objectives
* **Tenant Hierarchy**: Organizational structure supporting Organization -> Workspace -> Environment -> Project.
* **Workspace Isolation**: Logical partitioning of database records, caches, and workers.
* **Policy Engine Access Control**: Modular policy engine supporting **RBAC**, **ABAC**, **Resource Policies**, and **Execution Policies** (supporting integration with OPA/Cedar).
* **HashiCorp Vault Integration**: Secure credential vault with automatic secret rotation.
* **Quotas & Cost Tracking**: Token usage tracking, budget enforcement, and node rate limiting.

---

## Phase 11: MCP Integration, Package Marketplace & CLI
Enabling modular extension distributions.

### Key Objectives
* **MCP Provider Registry Integration**: Model Context Protocol (MCP) clients register as drivers inside the `Provider Registry`.
* **Fluxa CLI**: Project initializer and package installer (`fluxa install <package>`).
* **Package Marketplace**: Registry feed supporting dependency installation.
* **Package Signing & Verification**: Manifest, Signature, Hash, Publisher, and Dependency validation.
* **Package Compatibility**: Version constraint validations (e.g. `Fluxa >= 1.3`, `Python >= 3.12`, etc.).

---

## Phase 12: Production Hardening, Observability & Kubernetes
Preparing the operating system layer for cloud scale.

### Key Objectives
* **Distributed Scheduler**: Queue and priority scheduling (Scheduler -> Queue -> Workers -> Temporal).
* **Kubernetes Orchestration**: Helm charts, horizontal scaling workers, and autoscaling.
* **Production Observability**: Distributed tracing, Prometheus metrics, and OpenTelemetry.
* **Chaos Testing**: Simulating network partitions and worker failures for resilience verification.
* **Disaster Recovery**: Automated backups, restore, cross-region replication, and point-in-time recovery.

---

## Phase 13: Developer Experience (Optional/Future)
Developer tools and SDKs to support external platform builders.

### Key Objectives
* **Developer SDKs**: Official Python and TypeScript SDKs for programmatically interacting with the platform.
* **DX Frameworks**: Plugin Generator, Package Templates, Testing Framework, Local Emulator, Mock Providers, and Debug CLI.
* **Documentation Generator**: Auto-generates OpenAPI, Node/Tool/Package documentation, and SDK code examples.
