import json
import os
from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.core.services.variables.resolver import VariableResolver

@NodeExecutorRegistry.register("file_storage")
class FileStorageNodeExecutor(BaseNodeExecutor):
    """
    File Storage executor to read or write files.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "file_storage")
        operation = node_data.get("operation", "read")  # 'read' or 'write'
        file_path_raw = node_data.get("filePath", "/data/output.json")
        
        # Resolve variables in file path
        file_path = VariableResolver.resolve(file_path_raw, context.variables, context.node_outputs)
        
        # If relative, resolve relative to workspace root (d:\Fluxa)
        if not os.path.isabs(file_path):
            # Check for leading slash/dot
            if file_path.startswith("/") or file_path.startswith("\\"):
                file_path = file_path[1:]
            file_path = os.path.join(r"d:\Fluxa", file_path)
            
        if operation == "write":
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            content_raw = node_data.get("content", "")
            content = VariableResolver.resolve(content_raw, context.variables, context.node_outputs)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(content))
                
            context.node_outputs[node_id] = {
                "status": "success",
                "filePath": file_path
            }
        else:
            # Read operation
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Try parsing as JSON
            try:
                json_data = json.loads(content)
            except Exception:
                json_data = {}
                
            context.node_outputs[node_id] = {
                "content": content,
                "json_data": json_data,
                "filePath": file_path
            }
            
        return context
