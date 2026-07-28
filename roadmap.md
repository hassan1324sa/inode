# Fluxa Master Roadmap - Remaining Phases (8 to 12)

This document outlines the strategic roadmap and technical architecture for the remaining phases of the Fluxa Agentic Operating System, updated with approved enterprise-grade modular designs.

---

## Phase 8: Agent Runtime, Planner, Memory & Knowledge Layer
Transforms Fluxa from a structured workflow executor into a reasoning Agent Kernel.

### 8.1 Agent Kernel & Reasoning Loop
* **Runtime Abstraction**: `AgentRuntime` and `WorkflowRuntime` share a common `Runtime` interface, keeping agent reasoning decoupled from workflow orchestrations.
* **Planner & Abstract Plan**: The `Planner` produces a modular `Plan` (reasoning steps/tool dependencies) executed by a separate `PlanExecutor`, enabling human approvals and parallelization.
* **Reason-Tool-Observe Loop**: Core engine execution loop resolving thoughts, executing tools, and capturing outputs.
* **Planner Strategy Interface**: Swappable planner engines (e.g., `SequentialPlanner`, `ReActPlanner`, `PlanAndSolvePlanner`, `TreeOfThoughtPlanner`).
* **Tool Capability Negotiation**: Tool execution flows through standard stages: **Discover**, **Validate**, **Negotiate**, and **Execute** for dynamic tool selection.

### 8.2 Memory vs. Knowledge Layer
* **Memory Layer**:
  * **Short-term**: Session execution context variables.
  * **Long-term/Episodic**: Localized vector embeddings of past execution runs. Swappable via `MemoryProvider` abstraction (`ChromaMemory`, `QdrantMemory`, `PostgresMemory`, `RedisMemory`).
* **Knowledge Layer**: Separated document store, embeddings, chunking pipeline, semantic search retrieval, and source citation engine.
* **Skills as Packages**: Reusable package structures containing a manifest, tool schemas, templates, and optional memory rules.
* **Event-Driven Agent Communication**: Agents communicate strictly via the task dispatcher and `ExecutionEventBus`.

---

## Phase 9: Dashboard, API & Visual Live Builder
Building user interfaces for visual building and runtime monitoring.

### 9.1 Backend API & Visual Builder
* **FastAPI Backend Endpoints**: Full API coverage for compiling, triggering, and managing workflows and agent sessions.
* **Visual Live Builder Bindings**: Dynamically generates visual UI blocks matching registry schemas.

### 9.2 Real-time Visual Execution
* **WebSocket logs & state**: Real-time event streams capturing running executions.
* **Execution Replay**: Allows visual state debugging of snapshot history logs.

---

## Phase 10: Multi-Tenant Architecture & Enterprise Security
Adding security and cost tracking.

### Key Objectives
* **Workspace Isolation**: Logical partitioning of database records, caches, and workers per Tenant ID.
* **Access Control**: Dynamic Attribute-Based Access Control (ABAC) in addition to Role-Based Access Control (RBAC).
* **HashiCorp Vault Integration**: Secure credential vault with automatic secret rotation.
* **Quotas & Cost Tracking**: Token usage tracking, budget enforcement, and node rate limiting.
* **AI Governance**: Prompt Versioning, Prompt Registry, Model Routing with Fallbacks, Cost Policies, and Safety Guardrails.

---

## Phase 11: MCP Integration, Package Marketplace & CLI
Enabling modular extension distributions.

### Key Objectives
* **MCP Provider Registry Integration**: Model Context Protocol (MCP) clients register as drivers inside the `Provider Registry`, exposing external tool servers seamlessly.
* **Fluxa CLI**: Project initializer and package installer (`fluxa install <package>`).
* **Package Marketplace**: Registry feed supporting dependency installation.

---

## Phase 12: Production Hardening, Observability & Kubernetes
Preparing the operating system layer for cloud scale.

### Key Objectives
* **Worker Scheduler & Worker Pool**: Core scaling scheduling layer allowing vertical and horizontal worker pools before Kubernetes provisioning.
* **Kubernetes Orchestration**: Helm charts, horizontal scaling workers, and autoscaling.
* **Production Observability**: Distributed tracing, Prometheus metrics, and OpenTelemetry.
* **Chaos & Disaster Recovery**: Chaos testing and active-active failovers.
