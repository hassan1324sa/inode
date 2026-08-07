import re
from typing import Any, Dict

class VariableResolver:
    """
    Type-aware variable resolver. Extracts variables from placeholder formats like:
    {{current_row.sales}} or resolves full templates like "Hello {{current_row.name}}".
    """
    
    # Matches placeholders like {{path.to.variable}}
    PLACEHOLDER_PATTERN = re.compile(r'\{\{\s*([a-zA-Z0-9_\-\.]+)\s*\}\}')

    @classmethod
    def resolve(cls, value: Any, context_variables: Dict[str, Any], node_outputs: Dict[str, Any]) -> Any:
        """
        Recursively resolves variables in strings, dicts, and lists.
        """
        if isinstance(value, str):
            return cls._resolve_string(value, context_variables, node_outputs)
        elif isinstance(value, dict):
            return {k: cls.resolve(v, context_variables, node_outputs) for k, v in value.items()}
        elif isinstance(value, list):
            return [cls.resolve(item, context_variables, node_outputs) for item in value]
        return value

    @classmethod
    def _resolve_string(cls, val_str: str, context_variables: Dict[str, Any], node_outputs: Dict[str, Any]) -> Any:
        # Check if the string is exactly a single placeholder, e.g. "{{current_row.sales}}"
        match = cls.PLACEHOLDER_PATTERN.fullmatch(val_str.strip())
        if match:
            path = match.group(1)
            return cls._resolve_path(path, context_variables, node_outputs)

        # Otherwise, perform template substitution (string interpolation)
        def replace(m):
            path = m.group(1)
            resolved = cls._resolve_path(path, context_variables, node_outputs)
            return str(resolved) if resolved is not None else ""

        return cls.PLACEHOLDER_PATTERN.sub(replace, val_str)

    @classmethod
    def _resolve_path(cls, path: str, context_variables: Dict[str, Any], node_outputs: Dict[str, Any]) -> Any:
        """
        Resolves a path like 'current_row.sales' or 'node_1.output.text' from context.
        """
        parts = path.split('.')
        root = parts[0]

        # Explicit support for "variables" root namespace
        if root == "variables":
            if len(parts) > 1:
                current = context_variables
                parts = parts[1:]
            else:
                return context_variables
        elif root in node_outputs:
            current = node_outputs[root]
            parts = parts[1:]
        elif root in context_variables:
            current = context_variables[root]
            parts = parts[1:]
        else:
            current = context_variables.get(root)
            parts = parts[1:]

        if current is None:
            return None

        # Resolve nested keys
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current
