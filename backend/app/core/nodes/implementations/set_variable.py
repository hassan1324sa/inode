from typing import Any
from app.core.nodes.base import BaseNode, NodeContext
from app.core.nodes.registry import NodeRegistry

@NodeRegistry.register("set_variable")
class SetVariableNode(BaseNode):
    """
    A node that sets a specific variable in the workflow context.
    """
    variable_name: str
    variable_value: Any

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Set the variable in the context and return the updated context.
        """
        context.set(self.variable_name, self.variable_value)
        return context
