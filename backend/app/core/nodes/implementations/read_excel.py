import csv
import os
from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

@NodeExecutorRegistry.register("read-excel")
class ReadExcelNodeExecutor(BaseNodeExecutor):
    """
    Reads structured customer rows from CSV or simulated Excel files.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        file_path = node_data.get("file_path")
        output_var = node_data.get("output_var", "rows")
        
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        rows = []
        with open(file_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert Sales to integer if available
                if "sales" in row:
                    try:
                        row["sales"] = int(row["sales"].replace(",", "").strip())
                    except ValueError:
                        pass
                rows.append(row)
                
        context.variables[output_var] = rows
        context.node_outputs[node_data.get("id", "read-excel")] = {"count": len(rows)}
        return context
