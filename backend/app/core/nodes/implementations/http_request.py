import httpx
from typing import Dict, Any, Optional
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.core.security.ssrf_guard import SSRFSafeTransport, validate_url_security
from app.core.security.context import SecurityException

@NodeExecutorRegistry.register("http_request")
class HTTPRequestNodeExecutor(BaseNodeExecutor):
    """
    Executes external HTTP REST requests safely with SSRF protection,
    DNS multi-IP resolution verification, and redirect safeguards.
    """

    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        url = node_data.get("url")
        method = (node_data.get("method") or "GET").upper()
        headers_input = node_data.get("headers") or {}
        body = node_data.get("body")

        if not url:
            raise ValueError("HTTP Request Node: Missing required 'url' parameter.")

        # 1. Pre-flight SSRF Validation (Parse Scheme, Hostname, DNS Resolution, IP Ranges)
        validate_url_security(url)

        # Parse headers if passed as JSON string
        if isinstance(headers_input, str):
            import json
            try:
                headers = json.loads(headers_input)
            except Exception:
                headers = {}
        else:
            headers = dict(headers_input)

        # 2. Execute Async Request using SSRFSafeTransport
        async with httpx.AsyncClient(transport=SSRFSafeTransport(), timeout=15.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body if isinstance(body, (str, bytes)) else None,
                    json=body if isinstance(body, dict) else None
                )
                
                # Check status
                response.raise_for_status()
                
                try:
                    res_payload = response.json()
                except Exception:
                    res_payload = response.text

                # Store output in ExecutionContext
                node_id = node_data.get("id", "http_node")
                context.node_outputs[node_id] = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": res_payload
                }
                return context

            except httpx.HTTPStatusError as e:
                raise ValueError(f"HTTP Request failed with status {e.response.status_code}: {e.response.text}")
            except SecurityException:
                raise
            except Exception as e:
                raise ValueError(f"HTTP Request execution error: {str(e)}")
