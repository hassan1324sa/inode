import ast
import operator
from typing import Any, Dict

class SafeExpressionEvaluator:
    """
    AST-based safe expression evaluator. Parses binary and boolean operators
    without relying on python's eval().
    """
    
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
        ast.Not: operator.not_,
    }

    @classmethod
    def evaluate(cls, expression: str, variables: Dict[str, Any]) -> bool:
        """
        Parses expression and evaluates it within variables context.
        Returns Boolean output.
        """
        if not expression:
            return False
            
        try:
            tree = ast.parse(expression.strip(), mode='eval')
            return bool(cls._eval_node(tree.body, variables))
        except Exception as e:
            raise ValueError(f"Expression evaluation error: {str(e)}")

    @classmethod
    def _eval_node(cls, node: ast.AST, variables: Dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
            
        elif isinstance(node, ast.Name):
            # Check variables context
            if node.id in variables:
                return variables[node.id]
            raise NameError(f"Name '{node.id}' is not defined in expression context")
            
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_OPERATORS:
                raise TypeError(f"Operator {op_type.__name__} is not allowed")
            left = cls._eval_node(node.left, variables)
            right = cls._eval_node(node.right, variables)
            return cls.ALLOWED_OPERATORS[op_type](left, right)
            
        elif isinstance(node, ast.Compare):
            left = cls._eval_node(node.left, variables)
            for op, comparator in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in cls.ALLOWED_OPERATORS:
                    raise TypeError(f"Comparison operator {op_type.__name__} is not allowed")
                right = cls._eval_node(comparator, variables)
                if not cls.ALLOWED_OPERATORS[op_type](left, right):
                    return False
                left = right
            return True
            
        elif isinstance(node, ast.BoolOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_OPERATORS:
                raise TypeError(f"Logical operator {op_type.__name__} is not allowed")
            
            values = [cls._eval_node(val, variables) for val in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
                
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_OPERATORS:
                raise TypeError(f"Unary operator {op_type.__name__} is not allowed")
            operand = cls._eval_node(node.operand, variables)
            return cls.ALLOWED_OPERATORS[op_type](operand)

        raise TypeError(f"Unsupported expression node type: {type(node).__name__}")
