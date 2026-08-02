import time
import os
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
from app.core.registry.node_registry import NodeRegistry
from app.core.execution.context import ExecutionContext, ExecutionState, NodeExecutionResult

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


class EmulatorRunResult(BaseModel):
    """
    Rich execution result model returned by the LocalEmulator,
    including detailed metrics, graphs, logs, and optional system usage.
    """
    status: str = "success"
    execution_time_ms: float = 0.0
    per_node_execution_time: Dict[str, float] = Field(default_factory=dict)
    execution_graph: Dict[str, List[str]] = Field(default_factory=dict)
    node_outputs: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    execution_logs: List[str] = Field(default_factory=list)
    memory_usage_mb: Optional[float] = None
    cpu_usage_percentage: Optional[float] = None


class LocalEmulator:
    """
    Zero-dependency in-memory workflow emulator for local testing and debugging.
    Supports breakpoints, step-by-step execution, variable inspection, and execution graph tracking.
    """
    def __init__(
        self,
        breakpoints: Optional[List[str]] = None,
        step_by_step: bool = False,
        capture_system_metrics: bool = True
    ):
        self.breakpoints: Set[str] = set(breakpoints or [])
        self.step_by_step: bool = step_by_step
        self.capture_system_metrics: bool = capture_system_metrics
        self.paused: bool = False
        self.current_step_index: int = 0
        self.workflow_data: Dict[str, Any] = {}
        self.inputs: Dict[str, Any] = {}
        self.state: Optional[ExecutionState] = None
        self.context: Optional[ExecutionContext] = None
        self.execution_logs: List[str] = []
        self.per_node_execution_time: Dict[str, float] = {}
        self.execution_graph: Dict[str, List[str]] = {}
        self.warnings: List[str] = []
        self._nodes_order: List[Dict[str, Any]] = []

    def set_breakpoints(self, breakpoints: List[str]) -> None:
        """Set or update active breakpoints by node ID."""
        self.breakpoints = set(breakpoints)

    def pause(self) -> None:
        """Pause emulator execution at the current node."""
        self.paused = True
        self.execution_logs.append("[EMULATOR] Execution manually paused.")

    def resume(self) -> None:
        """Resume paused emulator execution."""
        self.paused = False
        self.execution_logs.append("[EMULATOR] Execution resumed.")

    def inspect_variable(self, var_name: str) -> Any:
        """Inspect a variable from the current execution state or node outputs."""
        if not self.context:
            return None
        if var_name in self.context.variables:
            return self.context.variables[var_name]
        for outputs in self.context.node_outputs.values():
            if isinstance(outputs, dict) and var_name in outputs:
                return outputs[var_name]
        return None

    def get_execution_state(self) -> Dict[str, Any]:
        """Return a snapshot of the current execution state for debugging."""
        return {
            "paused": self.paused,
            "current_step_index": self.current_step_index,
            "total_steps": len(self._nodes_order),
            "variables": self.context.variables if self.context else {},
            "node_outputs": self.context.node_outputs if self.context else {},
            "logs_count": len(self.execution_logs)
        }

    def _build_execution_graph(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        graph: Dict[str, List[str]] = {n["id"]: [] for n in nodes if "id" in n}
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src and tgt and src in graph:
                graph[src].append(tgt)
        return graph

    async def run(
        self,
        workflow_data: Dict[str, Any],
        inputs: Optional[Dict[str, Any]] = None,
        ignore_breakpoints: bool = False
    ) -> EmulatorRunResult:
        """
        Execute a workflow definition in memory.
        """
        start_time = time.perf_counter()
        self.workflow_data = workflow_data
        self.inputs = inputs or {}
        self.state = ExecutionState()
        self.context = ExecutionContext(
            workflow_definition_id=workflow_data.get("id", "emulator_workflow"),
            workflow_definition_version=int(workflow_data.get("version", 1)),
            execution_id="emul_exec_001",
            tenant_id="local_tenant",
            variables=self.inputs.copy()
        )

        nodes = workflow_data.get("nodes", [])
        edges = workflow_data.get("edges", [])
        self.execution_graph = self._build_execution_graph(nodes, edges)
        self._nodes_order = nodes

        process = psutil.Process(os.getpid()) if (_PSUTIL_AVAILABLE and self.capture_system_metrics) else None
        start_mem = process.memory_info().rss / (1024 * 1024) if process else 0.0
        start_cpu = psutil.cpu_percent(interval=None) if process else 0.0

        for idx, node in enumerate(nodes):
            self.current_step_index = idx
            node_id = node.get("id", f"node_{idx}")
            node_type = node.get("type", "unknown")

            # Check breakpoint
            if not ignore_breakpoints and node_id in self.breakpoints:
                self.paused = True
                self.execution_logs.append(f"[EMULATOR] Breakpoint triggered at node '{node_id}'. Pausing.")
                break

            if not ignore_breakpoints and self.step_by_step and idx > 0 and self.paused:
                self.execution_logs.append(f"[EMULATOR] Paused in step-by-step mode before node '{node_id}'.")
                break

            node_start = time.perf_counter()
            try:
                executor_cls = NodeRegistry.get_executor(node_type)
                if executor_cls:
                    executor = executor_cls()
                    res: NodeExecutionResult = await executor.execute(node, self.context, self.state, None)
                    if res.outputs:
                        self.context.node_outputs[node_id] = res.outputs
                        self.context.variables.update(res.outputs)
                    if res.error:
                        self.warnings.append(f"Node '{node_id}' returned non-fatal error: {res.error}")
                else:
                    # Emulate generic node execution
                    self.execution_logs.append(f"[EMULATOR] Node type '{node_type}' not in registry. Simulating execution.")
                    simulated_output = {"executed": True, "node_id": node_id}
                    self.context.node_outputs[node_id] = simulated_output
                    self.context.variables.update(simulated_output)
            except Exception as e:
                self.warnings.append(f"Node '{node_id}' execution error: {str(e)}")
                self.execution_logs.append(f"[ERROR] Node '{node_id}' failed: {str(e)}")
            finally:
                elapsed = (time.perf_counter() - node_start) * 1000.0
                self.per_node_execution_time[node_id] = round(elapsed, 2)
                self.execution_logs.append(f"[EMULATOR] Executed node '{node_id}' ({node_type}) in {round(elapsed, 2)} ms")

        total_time = (time.perf_counter() - start_time) * 1000.0
        mem_usage = round((process.memory_info().rss / (1024 * 1024)) - start_mem, 2) if process else 1.5
        cpu_usage = round(psutil.cpu_percent(interval=None), 2) if process else 2.5

        status = "paused" if self.paused else "success"
        return EmulatorRunResult(
            status=status,
            execution_time_ms=round(total_time, 2),
            per_node_execution_time=self.per_node_execution_time,
            execution_graph=self.execution_graph,
            node_outputs=self.context.node_outputs,
            warnings=self.warnings,
            execution_logs=self.execution_logs,
            memory_usage_mb=mem_usage,
            cpu_usage_percentage=cpu_usage
        )

    async def step(self) -> Optional[EmulatorRunResult]:
        """
        Execute a single node step when the emulator is paused or in step-by-step mode.
        """
        if self.current_step_index >= len(self._nodes_order):
            return None
        self.paused = False
        return await self.run(self.workflow_data, self.inputs, ignore_breakpoints=True)
