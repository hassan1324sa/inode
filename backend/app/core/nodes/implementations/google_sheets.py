import json
import os
import logging
from typing import Dict, Any, List, Optional
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.core.security.secrets import VaultSecretProvider, SecretRef
from app.core.services.variables.resolver import VariableResolver

# Real Google API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger("fluxa.google_sheets")

class GoogleSheetsService:
    """
    Service abstraction for Google Sheets CRUD operations.
    Supports secure credential loading and fallbacks.
    """
    def __init__(self, spreadsheet_id: str, credentials_ref: Optional[Dict[str, Any]] = None):
        self.spreadsheet_id = spreadsheet_id
        self.credentials_ref = credentials_ref

    async def _get_creds(self):
        # 1. Try loading credentials from credentials_ref via Vault
        if self.credentials_ref:
            try:
                provider = VaultSecretProvider()
                ref = SecretRef(**self.credentials_ref)
                credentials_data = await provider.get(ref)
                if isinstance(credentials_data, str):
                    credentials_data = json.loads(credentials_data)
                return service_account.Credentials.from_service_account_info(
                    credentials_data,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
            except Exception as e:
                logger.warning(f"Failed to load Sheets credentials from Vault: {e}")

        # 2. Fallback to default credentials
        try:
            import google.auth
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
            return creds
        except Exception:
            return None

    async def read_rows(self, range_name: str = "Sheet1") -> Dict[str, Any]:
        creds = await self._get_creds()
        if not creds:
            raise ValueError("No Google Sheets credentials found. Please configure GOOGLE_APPLICATION_CREDENTIALS or the vault credential provider.")

        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get("values", [])
        if not values:
            return {"rows": [], "count": 0}
            
        headers = values[0]
        rows = []
        for row in values[1:]:
            row_dict = {}
            for i, val in enumerate(row):
                if i < len(headers):
                    row_dict[headers[i]] = val
            rows.append(row_dict)
            
        return {
            "rows": rows,
            "count": len(rows)
        }

    async def append_row(self, row: Dict[str, Any], range_name: str = "Sheet1") -> Dict[str, Any]:
        creds = await self._get_creds()
        if not creds:
            raise ValueError("No Google Sheets credentials found.")
            
        service = build("sheets", "v4", credentials=creds)
        sheet_result = service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()
        
        values = sheet_result.get("values", [])
        if not values:
            headers = list(row.keys())
            service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": [headers]}
            ).execute()
            values = [headers]
            
        headers = values[0]
        row_values = [row.get(h, "") for h in headers]
        
        append_res = service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_values]}
        ).execute()
        
        return {"status": "success", "result": append_res}

    async def update_row(self, row_id: Any, updates: Dict[str, Any], range_name: str = "Sheet1") -> Dict[str, Any]:
        creds = await self._get_creds()
        if not creds:
            raise ValueError("No Google Sheets credentials found.")
            
        service = build("sheets", "v4", credentials=creds)
        sheet_result = service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()
        
        values = sheet_result.get("values", [])
        if not values:
            return {"status": "error", "message": "Sheet is empty."}
            
        headers = values[0]
        id_col_indices = [i for i, h in enumerate(headers) if h.lower() in ("id", "email", "key")]
        if not id_col_indices:
            id_col_indices = [0]
            
        row_index = -1
        for idx, row in enumerate(values[1:], start=2):
            for col_idx in id_col_indices:
                if col_idx < len(row) and str(row[col_idx]) == str(row_id):
                    row_index = idx
                    break
            if row_index != -1:
                break
                
        if row_index == -1:
            return {"status": "error", "message": f"Row ID {row_id} not found."}
            
        current_row = values[row_index - 1]
        while len(current_row) < len(headers):
            current_row.append("")
            
        for k, v in updates.items():
            if k in headers:
                col_idx = headers.index(k)
                current_row[col_idx] = v
                
        update_range = f"{range_name}!A{row_index}"
        service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=update_range,
            valueInputOption="USER_ENTERED",
            body={"values": [current_row]}
        ).execute()
        
        return {"status": "success", "updated_row_index": row_index}

    async def delete_row(self, row_id: Any, range_name: str = "Sheet1") -> Dict[str, Any]:
        creds = await self._get_creds()
        if not creds:
            raise ValueError("No Google Sheets credentials found.")
            
        service = build("sheets", "v4", credentials=creds)
        spreadsheet = service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        sheet_metadata = None
        for s in spreadsheet.get("sheets", []):
            if s.get("properties", {}).get("title") == range_name:
                sheet_metadata = s
                break
        if not sheet_metadata:
            sheet_metadata = spreadsheet.get("sheets", [])[0]
            
        sheet_id = sheet_metadata["properties"]["sheetId"]
        
        sheet_result = service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()
        values = sheet_result.get("values", [])
        if not values:
            return {"status": "error", "message": "Sheet is empty."}
            
        headers = values[0]
        id_col_indices = [i for i, h in enumerate(headers) if h.lower() in ("id", "email", "key")]
        if not id_col_indices:
            id_col_indices = [0]
            
        row_index = -1
        for idx, row in enumerate(values[1:], start=1):
            for col_idx in id_col_indices:
                if col_idx < len(row) and str(row[col_idx]) == str(row_id):
                    row_index = idx
                    break
            if row_index != -1:
                break
                
        if row_index == -1:
            return {"status": "error", "message": f"Row ID {row_id} not found."}
            
        body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": row_index,
                            "endIndex": row_index + 1
                        }
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body=body
        ).execute()
        
        return {"status": "success", "deleted_row_index": row_index}


@NodeExecutorRegistry.register("google_sheets")
class GoogleSheetsNodeExecutor(BaseNodeExecutor):
    """
    Google Sheets Executor executing CRUD actions on spreadsheet.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "google_sheets")
        operation = node_data.get("operation", "read")  # read, append, update, delete
        spreadsheet_id_raw = node_data.get("spreadsheetId", "default_sheet")
        range_name_raw = node_data.get("range", "Sheet1")
        
        spreadsheet_id = VariableResolver.resolve(spreadsheet_id_raw, context.variables, context.node_outputs)
        range_name = VariableResolver.resolve(range_name_raw, context.variables, context.node_outputs)
        
        credentials_ref = node_data.get("credentials_ref")
        service = GoogleSheetsService(spreadsheet_id, credentials_ref)
        
        if operation == "read":
            result = await service.read_rows(range_name)
        elif operation == "append":
            row_raw = node_data.get("row", {})
            if isinstance(row_raw, str):
                try:
                    row_raw = json.loads(row_raw)
                except Exception:
                    row_raw = {}
            row = {k: VariableResolver.resolve(v, context.variables, context.node_outputs) for k, v in row_raw.items()}
            result = await service.append_row(row, range_name)
        elif operation == "update":
            row_id_raw = node_data.get("rowId")
            row_id = VariableResolver.resolve(row_id_raw, context.variables, context.node_outputs)
            updates_raw = node_data.get("updates", {})
            if isinstance(updates_raw, str):
                try:
                    updates_raw = json.loads(updates_raw)
                except Exception:
                    updates_raw = {}
            updates = {k: VariableResolver.resolve(v, context.variables, context.node_outputs) for k, v in updates_raw.items()}
            result = await service.update_row(row_id, updates, range_name)
        elif operation == "delete":
            row_id_raw = node_data.get("rowId")
            row_id = VariableResolver.resolve(row_id_raw, context.variables, context.node_outputs)
            result = await service.delete_row(row_id, range_name)
        else:
            raise ValueError(f"Unsupported Google Sheets operation: {operation}")
            
        context.node_outputs[node_id] = result
        return context

from app.core.registry.node_registry import NodeRegistry, NodeManifest, NodeCapabilities

NodeRegistry.register(
    NodeManifest(
        id="google_sheets",
        version="1.0.0",
        author="System",
        category="Files",
        capabilities=NodeCapabilities(supports_retry=True, requires_network=True),
        inputs={
            "operation": {"type": "string"},
            "spreadsheetId": {"type": "string"},
            "range": {"type": "string"},
            "row": {"type": "object"},
            "updates": {"type": "object"},
            "rowId": {"type": "string"}
        },
        outputs={
            "rows": {"type": "array"},
            "count": {"type": "integer"}
        }
    ),
    GoogleSheetsNodeExecutor
)
