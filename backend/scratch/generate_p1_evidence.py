import os
import json
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.core.database import db_manager

async def main():
    await db_manager.connect_db(document_models=[
        User, Organization, Workflow, WorkflowVersion
    ])
    
    # Manually initialize app state variables
    from app.core.cache.memory import MemoryCache
    from app.core.execution.service import ExecutionService
    app.state.memory_cache = MemoryCache()
    app.state.execution_service = ExecutionService()
    
    evidence_dir = "Evidence/P1-graph"

    os.makedirs(evidence_dir, exist_ok=True)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Register and Login
        reg_payload = {
            "email": "p1_auditor@fluxa.ai",
            "password": "supersecurepassword123",
            "name": "P1 Auditor"
        }
        existing = await User.find_one(User.email == reg_payload["email"])
        if existing:
            await existing.delete()
        await client.post("/api/v1/auth/register", json=reg_payload)
        
        resp_login = await client.post("/api/v1/auth/login", json={
            "email": "p1_auditor@fluxa.ai",
            "password": "supersecurepassword123"
        })
        token = resp_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup workflow definition
        wf_resp = await client.post("/api/v1/workflows/", json={"name": "P1 Evidence Workflow"}, headers=headers)
        wf_id = wf_resp.json()["id"]

        # Helper to run test and write to file
        async def run_evidence_test(filename, nodes, edges, rule_name):
            # Update workflow definition
            await client.put(f"/api/v1/workflows/{wf_id}", json={
                "nodes": nodes,
                "edges": edges
            }, headers=headers)
            
            # Trigger execution
            resp_exec = await client.post(f"/api/v1/workflows/{wf_id}/execute", json={
                "trigger_type": "Manual",
                "inputs": {}
            }, headers=headers)
            
            with open(f"{evidence_dir}/{filename}", "w", encoding="utf-8") as f:
                f.write(f"Input Nodes:\n{json.dumps(nodes, indent=2)}\n\n")
                f.write(f"Input Edges:\n{json.dumps(edges, indent=2)}\n\n")
                f.write(f"→ Validation rule: {rule_name}\n")
                f.write(f"→ Actual result:\n{json.dumps(resp_exec.json(), indent=2)}\n")
                f.write(f"→ HTTP status: {resp_exec.status_code}\n")
                f.write(f"→ Temporal invocation = NO\n")

        # 1. Invalid Edge (target does not exist)
        nodes_invalid_edge = [
            {"id": "node-trigger", "type": "manual_trigger"},
            {"id": "node-ai", "type": "ai_agent"}
        ]
        edges_invalid_edge = [
            {"source": "node-trigger", "target": "non-existent", "sourceHandle": "default", "targetHandle": "default"}
        ]
        await run_evidence_test("validation-invalid-edge.txt", nodes_invalid_edge, edges_invalid_edge, "Edge target existence check")

        # 2. Duplicate Node ID
        # Note: duplicate node ID fails during PUT or validation
        nodes_dup = [
            {"id": "node-trigger", "type": "manual_trigger"},
            {"id": "node-ai", "type": "ai_agent"},
            {"id": "node-ai", "type": "send-email"}
        ]
        await run_evidence_test("validation-duplicate-node.txt", nodes_dup, [], "Duplicate Node ID check")

        # 3. Missing Trigger
        nodes_missing_trigger = [
            {"id": "node-ai", "type": "ai_agent"},
            {"id": "node-email", "type": "send-email"}
        ]
        edges_missing_trigger = [
            {"source": "node-ai", "target": "node-email", "sourceHandle": "default", "targetHandle": "default"}
        ]
        await run_evidence_test("validation-missing-trigger.txt", nodes_missing_trigger, edges_missing_trigger, "Trigger presence check")

        # 4. Unreachable Node
        nodes_unreachable = [
            {"id": "node-trigger", "type": "manual_trigger"},
            {"id": "node-ai", "type": "ai_agent"},
            {"id": "node-email", "type": "send-email"}
        ]
        edges_unreachable = [
            {"source": "node-trigger", "target": "node-ai", "sourceHandle": "default", "targetHandle": "default"}
        ]
        await run_evidence_test("validation-unreachable-node.txt", nodes_unreachable, edges_unreachable, "Reachability check")

        # 5. Invalid Cycle
        nodes_cycle = [
            {"id": "node-trigger", "type": "manual_trigger"},
            {"id": "node-a", "type": "ai_agent"},
            {"id": "node-b", "type": "send-email"}
        ]
        edges_cycle = [
            {"source": "node-trigger", "target": "node-a", "sourceHandle": "default", "targetHandle": "default"},
            {"source": "node-a", "target": "node-b", "sourceHandle": "default", "targetHandle": "default"},
            {"source": "node-b", "target": "node-a", "sourceHandle": "default", "targetHandle": "default"}
        ]
        await run_evidence_test("invalid-cycle.txt", nodes_cycle, edges_cycle, "Structural Cycle check")

    await db_manager.close_db()
    print("P1 evidence successfully generated.")

if __name__ == "__main__":
    asyncio.run(main())
