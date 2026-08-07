from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.core.services.variables.resolver import VariableResolver
from app.core.services.expressions.evaluator import SafeExpressionEvaluator

@NodeExecutorRegistry.register("conditional")
class ConditionalNodeExecutor(BaseNodeExecutor):
    """
    Evaluates comparison expressions dynamically and outputs branch targeting.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "conditional")
        
        # 1. Check if user configured a dynamic expression, e.g. "current_row.sales > 15000"
        expression = node_data.get("expression")
        
        result = False
        if expression:
            # Resolve placeholders like "{{current_row.sales}}" inside the expression string
            resolved_expr = VariableResolver.resolve(expression, context.variables, context.node_outputs)
            try:
                # Safe evaluation using Python AST
                result = SafeExpressionEvaluator.evaluate(str(resolved_expr), {})
            except Exception:
                result = False
        else:
            # Fallback legacy support for hardcoded config comparison
            field = node_data.get("field", "sales")
            operator = node_data.get("operator", ">")
            target_value = node_data.get("value", 15000)
            
            # Resolve target field dynamically if it contains placeholders, otherwise lookup in current_row
            row = context.variables.get("current_row", {})
            val = row.get(field) if isinstance(row, dict) else None
            
            try:
                if val is not None:
                    if operator == ">":
                        result = float(val) > float(target_value)
                    elif operator == "<":
                        result = float(val) < float(target_value)
                    elif operator == "==":
                        result = str(val) == str(target_value)
            except Exception:
                result = False

        # Set compatibility states
        context.variables["last_condition_result"] = result
        
        # Set node outputs for Graph Traversal
        branch_taken = "true" if result else "false"
        context.node_outputs[node_id] = {
            "result": result,
            "branch": branch_taken,
            "output_handle": branch_taken
        }
        
        return context

