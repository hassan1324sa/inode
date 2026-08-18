import logging
import json
from typing import Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

logger = logging.getLogger("fluxa.transform_json")

def safe_extract(data: Any, path: str) -> Any:
    """Basic extraction logic instead of full jq or eval for security."""
    parts = path.strip().split(".")
    current = data
    for part in parts:
        if not part:
            continue
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current

@NodeExecutorRegistry.register("transform_json")
class TransformJsonExecutor(BaseNodeExecutor):
    """
    Transforms JSON data using a basic path mapping.
    """
    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        node_id = context.current_node
        node_config = context.workflow.get_node(node_id)
        if not node_config:
            raise ValueError(f"Node {node_id} not found in workflow")

        data = node_config.data
        query = data.get("query", "")
        
        # Get input data from previous node or variables
        input_data = context.variables.get("transform_input", {})
        
        if not query:
            raise ValueError("Query is required for JSON transformation.")
            
        logger.info(f"Transforming JSON with query: {query}")
        
        # Extremely basic transformation implementation
        # To avoid 'eval' for security, we only support direct mapping like '{"id": ".data.id"}'
        # or just single extraction like '.data.users'
        try:
            if query.startswith("{") and query.endswith("}"):
                # Basic mapping
                mapping = json.loads(query)
                output = {}
                for k, v in mapping.items():
                    if isinstance(v, str) and v.startswith("."):
                        output[k] = safe_extract(input_data, v)
                    else:
                        output[k] = v
            elif query.startswith("."):
                # Single extraction
                output = safe_extract(input_data, query)
            else:
                # Unsupported query format fallback
                raise ValueError("Unsupported query format. Use a simple path (e.g. '.data.items') or a JSON mapping dict where values are paths.")
        except Exception as e:
            logger.error(f"Failed to transform JSON: {e}")
            raise ValueError(f"Malformed input or invalid transformation query: {str(e)}")

        context.node_outputs[node_id] = {
            "status": "success",
            "transformed": output
        }
        return context
