from typing import Dict, Any, List, Optional


class WorkflowBuilder:
    """
    Fluent Workflow Builder API for programmatically defining workflows, nodes, connections,
    parallel branches, conditionals, and loops.
    """
    def __init__(self, workflow_id: str = "workflow_1", name: str = "Workflow"):
        self.workflow_id = workflow_id
        self.name = name
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []
        self._node_ids: set = set()

    def add_node(self, node_id: str, node_type: str, inputs: Optional[Dict[str, Any]] = None) -> "WorkflowBuilder":
        """Backwards-compatible method for adding a node."""
        if node_id in self._node_ids:
            raise ValueError(f"Node ID '{node_id}' already exists in workflow builder.")
        self.nodes.append({"id": node_id, "type": node_type, "inputs": inputs or {}})
        self._node_ids.add(node_id)
        return self

    def node(self, node_id: str, node_type: str, inputs: Optional[Dict[str, Any]] = None) -> "WorkflowBuilder":
        """Fluent alias for add_node."""
        return self.add_node(node_id, node_type, inputs=inputs)

    def connect(
        self,
        source: str,
        target: str,
        condition: Optional[str] = None
    ) -> "WorkflowBuilder":
        """Connect two nodes with an optional expression condition."""
        if source not in self._node_ids or target not in self._node_ids:
            raise ValueError(f"Both source '{source}' and target '{target}' must be added before connecting.")
        edge = {"source": source, "target": target}
        if condition:
            edge["condition"] = condition
        self.edges.append(edge)
        return self

    def parallel(self, *node_ids: str) -> "WorkflowBuilder":
        """
        Fluent helper to indicate multiple nodes run in parallel.
        Annotates nodes with parallel group tags if present.
        """
        for nid in node_ids:
            if nid not in self._node_ids:
                raise ValueError(f"Node ID '{nid}' not found in builder.")
            for node in self.nodes:
                if node["id"] == nid:
                    node["parallel_group"] = True
        return self

    def condition(
        self,
        node_id: str,
        true_target: str,
        false_target: str,
        expr: str = "True"
    ) -> "WorkflowBuilder":
        """
        Fluent helper for branching conditionals from a decision node to true/false targets.
        """
        self.connect(node_id, true_target, condition=f"({expr}) == True")
        self.connect(node_id, false_target, condition=f"({expr}) == False")
        return self

    def loop(
        self,
        node_id: str,
        max_iterations: int = 5
    ) -> "WorkflowBuilder":
        """
        Fluent helper to configure a node as a loop execution block.
        """
        for node in self.nodes:
            if node["id"] == node_id:
                node["loop_config"] = {"max_iterations": max_iterations}
        return self

    def build(self) -> Dict[str, Any]:
        """Compile and return the complete workflow dictionary representation."""
        return {
            "id": self.workflow_id,
            "name": self.name,
            "nodes": self.nodes,
            "edges": self.edges
        }
