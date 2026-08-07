from typing import List, Dict, Any, Optional
from app.core.nodes.registry import NodeContractRegistry, TriggerRegistry

class WorkflowValidationError(ValueError):
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or [message]

class GraphValidator:
    @classmethod
    def validate_graph(cls, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        errors = []
        if not nodes:
            raise WorkflowValidationError("Workflow must contain at least one node.", ["Workflow must contain at least one node."])

        # 1. IDs: Check for duplicate node IDs
        node_ids = set()
        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                errors.append("All nodes must have an 'id'.")
                continue
            if node_id in node_ids:
                errors.append(f"Duplicate node ID detected: {node_id}")
            node_ids.add(node_id)

        if errors:
            raise WorkflowValidationError("Duplicate node IDs or missing IDs", errors)

        node_map = {n["id"]: n for n in nodes}

        # 2. Edge existence
        seen_edges = set()
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            src_h = edge.get("sourceHandle")
            tgt_h = edge.get("targetHandle")

            if not src or not tgt:
                errors.append(f"Edge missing source or target: {edge}")
                continue

            if src not in node_map:
                errors.append(f"Edge source '{src}' does not exist.")
            if tgt not in node_map:
                errors.append(f"Edge target '{tgt}' does not exist.")

            edge_key = (src, tgt, src_h, tgt_h)
            if edge_key in seen_edges:
                errors.append(f"Duplicate edge detected: {src} -> {tgt} ({src_h} -> {tgt_h})")
            seen_edges.add(edge_key)

        if errors:
            raise WorkflowValidationError("Edge existence or duplication failures", errors)

        # 3. Handle validity
        for edge in edges:
            src = edge["source"]
            tgt = edge["target"]
            src_h = edge.get("sourceHandle") or "default"
            tgt_h = edge.get("targetHandle") or "default"

            src_node = node_map[src]
            tgt_node = node_map[tgt]
            
            src_contract = NodeContractRegistry.get_contract(src_node.get("type"))
            tgt_contract = NodeContractRegistry.get_contract(tgt_node.get("type"))

            if src_contract:
                if src_h not in src_contract.output_handles:
                    errors.append(f"Invalid output handle '{src_h}' for node type '{src_node.get('type')}' on node '{src}'")
            if tgt_contract:
                if tgt_h not in tgt_contract.input_handles:
                    errors.append(f"Invalid input handle '{tgt_h}' for node type '{tgt_node.get('type')}' on node '{tgt}'")

        if errors:
            raise WorkflowValidationError("Invalid handles", errors)

        # 4. Root Trigger check
        triggers = []
        for node in nodes:
            n_type = node.get("type")
            if TriggerRegistry.is_trigger(n_type):
                triggers.append(node["id"])

        if len(triggers) == 0:
            errors.append("Workflow must contain exactly one trigger node (none found).")
        elif len(triggers) > 1:
            errors.append(f"Workflow must contain exactly one trigger node. Found multiple: {', '.join(triggers)}")

        if errors:
            raise WorkflowValidationError("Trigger check failed", errors)

        trigger_id = triggers[0]

        # Build adjacency mapping for reachability and cycle checks
        adj: Dict[str, List[str]] = {n_id: [] for n_id in node_ids}
        for edge in edges:
            adj[edge["source"]].append(edge["target"])

        # 5. Reachability Check
        visited = set()
        def dfs_reach(node_id: str):
            visited.add(node_id)
            for neighbor in adj.get(node_id, []):
                if neighbor not in visited:
                    dfs_reach(neighbor)

        dfs_reach(trigger_id)

        unreachable = node_ids - visited
        if unreachable:
            for un in unreachable:
                errors.append(f"Node '{un}' is unreachable from trigger '{trigger_id}'.")

        if errors:
            raise WorkflowValidationError("Unreachable nodes detected", errors)

        # 6. Cycle Detection (Reject arbitrary structural cycles)
        state = {n_id: 0 for n_id in node_ids}
        cycle_nodes = []

        def dfs_cycle(node_id: str) -> bool:
            state[node_id] = 1
            for neighbor in adj.get(node_id, []):
                if state[neighbor] == 1:
                    cycle_nodes.append(f"{node_id} -> {neighbor}")
                    return True
                elif state[neighbor] == 0:
                    if dfs_cycle(neighbor):
                        return True
            state[node_id] = 2
            return False

        has_cycle = False
        for n_id in node_ids:
            if state[n_id] == 0:
                if dfs_cycle(n_id):
                    has_cycle = True
                    break

        if has_cycle:
            errors.append(f"Structural cycle detected: {', '.join(cycle_nodes)}")

        if errors:
            raise WorkflowValidationError("Structural cycle check failed", errors)
