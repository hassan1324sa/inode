import csv
import os
from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext

@NodeExecutorRegistry.register("read_excel")
class ReadExcelNodeExecutor(BaseNodeExecutor):
    """
    Reads structured customer rows from CSV or simulated Excel files.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        file_path = node_data.get("file_path")
        output_var = node_data.get("output_var", "rows")
        
        import tempfile
        base_dir = os.path.abspath(tempfile.gettempdir())
        
        safe_rel_path = (file_path or "").lstrip("/\\")
        if ":" in safe_rel_path:
            safe_rel_path = safe_rel_path.split(":", 1)[1].lstrip("/\\")
            
        resolved_path = os.path.abspath(os.path.join(base_dir, safe_rel_path))
        if os.path.commonpath([base_dir, resolved_path]) != os.path.normpath(base_dir):
            raise ValueError(f"Invalid path traversal. Access to {file_path} is denied.")
            
        file_path = resolved_path
        
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        rows = []
        if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            headers = []
            for i, row in enumerate(sheet.iter_rows(values_only=True)):
                if i == 0:
                    headers = [str(c).lower().strip() if c else f"col_{j}" for j, c in enumerate(row)]
                else:
                    row_dict = {}
                    for j, c in enumerate(row):
                        if j < len(headers):
                            row_dict[headers[j]] = c
                    if "sales" in row_dict and row_dict["sales"] is not None:
                        try:
                            row_dict["sales"] = int(str(row_dict["sales"]).replace(",", "").strip())
                        except ValueError:
                            pass
                    rows.append(row_dict)
        else:
            with open(file_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert Sales to integer if available
                    if "sales" in row:
                        try:
                            row["sales"] = int(str(row["sales"]).replace(",", "").strip())
                        except ValueError:
                            pass
                    rows.append(row)
                
        context.variables[output_var] = rows
        context.node_outputs[node_data.get("id", "read-excel")] = {"count": len(rows)}
        return context
