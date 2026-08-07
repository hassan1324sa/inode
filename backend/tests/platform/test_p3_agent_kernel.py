import pytest
import asyncio
from app.core.agents.context import AgentContext
from app.core.agents.kernel import AgentKernel, PlanningPolicy, Plan, PlanStep
from app.core.agents.planner import ReActPlanner
from app.core.agents.tools import ToolRegistry, ToolExecutor, NativeTool, ToolMetadata
from app.core.agents.memory import MemoryLayer, LocalInMemoryMemory
from app.core.agents.governance import ModelRouter
from app.core.agents.executor import PlanExecutor

@pytest.fixture(autouse=True)
def clean_registries():
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()

@pytest.mark.anyio
async def test_planner_executor_temporal_isolation(monkeypatch):
    """
    Verifies that Planner and PlanExecutor boundaries are correctly preserved and
    transitioned using PlanExecutor without direct workflow I/O.
    """
    called_activities = []
    
    # Mock Temporal workflow's execute_activity to simulate real activity execution trace
    class MockTemporalWorkflow:
        @staticmethod
        def info():
            class MockInfo:
                def is_cancel_requested(self):
                    return False
            return MockInfo()
            
        @staticmethod
        async def execute_activity(activity_name, args, **kwargs):
            called_activities.append(activity_name)
            if activity_name == "plan_activity":
                # Return a basic React plan
                return {
                    "steps": [
                        {"tool_name": "math_tool", "args": {"val": 10}, "thought": "Need to calculate"}
                    ],
                    "is_completed": False,
                    "final_answer": None
                }
            if activity_name == "execute_tool_activity":
                return 20

    monkeypatch.setattr("temporalio.workflow.info", MockTemporalWorkflow.info)
    monkeypatch.setattr("temporalio.workflow.execute_activity", MockTemporalWorkflow.execute_activity)
    
    # Setup planners and tools
    router = ModelRouter()
    planner = ReActPlanner(model_router=router)
    memory_layer = MemoryLayer(semantic_provider=LocalInMemoryMemory())
    
    kernel = AgentKernel(
        planner=planner,
        tool_executor=ToolExecutor(),
        memory_layer=memory_layer,
        knowledge_layer=None,
        policy=PlanningPolicy(max_iterations=1)
    )
    
    context = AgentContext(
        session_id="session-p3-isolation-1",
        agent_id="agent-1",
        tenant_id="tenant-1",
        permissions=["math:calc"]
    )
    
    # Register math tool
    tool_meta = ToolMetadata(
        name="math_tool",
        description="Math operations",
        input_schema={"required": ["val"]},
        permissions=["math:calc"]
    )
    ToolRegistry.register_tool(NativeTool(metadata=tool_meta, handler=lambda args, ctx: args["val"] * 2))
    
    # Execute reasoning loop
    # In workflow mode, AgentKernel executes plan_activity and execute_tool_activity as activities
    result = await kernel.run(goal="Double 10", context=context)
    
    assert "plan_activity" in called_activities
    assert "execute_tool_activity" in called_activities
    assert len(result["plan"]["steps"]) == 1
    assert result["plan"]["steps"][0]["status"] == "COMPLETED"
    assert result["plan"]["steps"][0]["result"] == 20


@pytest.mark.anyio
async def test_plan_step_lifecycle(monkeypatch):
    """
    Verifies plan steps transition through: PLANNED -> VALIDATED -> RUNNING -> WAITING_FOR_TOOL -> OBSERVING -> COMPLETED
    """
    step_statuses = []
    
    # Mock execute_tool to track step state changes during execution
    class MockToolExecutor:
        async def execute_tool(self, tool_name, args, context):
            # Capture step statuses during tool execution (which happens inside execute_steps)
            for s in current_plan.steps:
                step_statuses.append(s.status)
            return "Life is good"

    executor = PlanExecutor(tool_executor=MockToolExecutor())
    
    current_plan = Plan(
        steps=[
            PlanStep(tool_name="test_tool", args={}, thought="Let's trace statuses", status="PLANNED")
        ]
    )
    
    context = AgentContext(session_id="sess-1", agent_id="agent-1", tenant_id="tenant-a")
    
    await executor.execute_steps(current_plan, context, [])
    
    # Verify lifecycle states
    # During execute_steps, before the tool execution runs, status transitions:
    # PLANNED -> VALIDATED -> RUNNING -> WAITING_FOR_TOOL
    assert "WAITING_FOR_TOOL" in step_statuses
    # After execute_steps finishes, final state must be COMPLETED
    assert current_plan.steps[0].status == "COMPLETED"


@pytest.mark.anyio
async def test_memory_tenant_isolation():
    """
    Verifies tenant isolation on persistent vector memory queries:
    Tenant A -> semantic query -> A data only
    Tenant B -> semantic query -> B data only
    """
    memory = LocalInMemoryMemory()
    
    # Add concepts with separate tenant IDs
    await memory.add_concept("c1", "Secret formula of Tenant A", [1.0, 0.0], tenant_id="tenant-A")
    await memory.add_concept("c2", "Secret formula of Tenant B", [1.0, 0.0], tenant_id="tenant-B")
    
    # Query under Tenant A scope
    res_A = await memory.query_concepts([1.0, 0.0], limit=5, tenant_id="tenant-A")
    assert len(res_A) == 1
    assert res_A[0].key == "c1"
    
    # Query under Tenant B scope
    res_B = await memory.query_concepts([1.0, 0.0], limit=5, tenant_id="tenant-B")
    assert len(res_B) == 1
    assert res_B[0].key == "c2"


@pytest.mark.anyio
async def test_tool_idempotency_check(monkeypatch):
    """
    Verifies that tool execution applies idempotency keys to prevent duplicate execution.
    """
    run_count = 0
    async def side_effect_handler(args, context):
        nonlocal run_count
        run_count += 1
        return f"Done {run_count}"

    tool_meta = ToolMetadata(
        name="effect_tool",
        description="Causes side effect",
        permissions=["test"]
    )
    ToolRegistry.register_tool(NativeTool(metadata=tool_meta, handler=side_effect_handler))
    
    context = AgentContext(
        session_id="test-session-idemp-tool-1",
        agent_id="agent-1",
        tenant_id="tenant-a",
        permissions=["test"]
    )
    
    from app.core.database import db_manager
    # Clear effects
    await db_manager.db["execution_effects"].delete_many({"execution_id": "test-session-idemp-tool-1"})
    
    executor = ToolExecutor()
    
    # 1. First execution (runs tool handler)
    res1 = await executor.execute_tool("effect_tool", {"action": "write"}, context)
    assert res1 == "Done 1"
    assert run_count == 1
    
    # 2. Second execution (retry, should return cached effect and bypass tool handler run)
    res2 = await executor.execute_tool("effect_tool", {"action": "write"}, context)
    assert res2 == "Done 1"
    assert run_count == 1  # Still 1, did not run duplicate side effect!
