from typing import Any, Dict
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

@NodeExecutorRegistry.register("set_variable")
class SetVariableExecutor(BaseNodeExecutor):
    """
    Node executor to set a variable in the execution context.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        var_name = node_data.get("variable_name")
        var_value = node_data.get("variable_value")
        if var_name:
            context.set_variable(var_name, var_value)
            # Record output of the node execution
            context.set_node_output(
                node_data.get("id", "unknown"),
                {"variable_name": var_name, "variable_value": var_value}
            )
        return context
