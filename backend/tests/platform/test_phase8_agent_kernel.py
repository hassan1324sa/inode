import pytest
import asyncio
from app.core.agents.context import AgentContext
from app.core.agents.kernel import AgentKernel, PlanningPolicy, Plan, PlanStep
from app.core.agents.planner import SequentialPlanner, ReActPlanner, PlanAndSolvePlanner, TreeOfThoughtPlanner
from app.core.agents.tools import ToolRegistry, ToolExecutor, NativeTool, ToolMetadata
from app.core.agents.memory import MemoryLayer, LocalInMemoryMemory, MemoryRecord
from app.core.agents.knowledge import KnowledgeLayer, ChunkingPipeline, Document
from app.core.agents.capabilities import UnifiedCapabilitySystem
from app.core.agents.governance import PromptTemplate, PromptRegistry, ModelRouter, SafetyPolicy, EvaluationLayer
from app.core.agents.skills import SkillPackage, SkillManifest

@pytest.fixture(autouse=True)
def mock_openrouter_calls():
    from unittest.mock import patch
    async def mock_generate_resp(self, prompt, system_prompt=None, context=None, target_model=None):
        text_out = "Solved."
        json_out = {"is_completed": True, "final_answer": "Processed successfully."}
        
        if "ReAct" in (system_prompt or ""):
            if "executed tool" in prompt:
                json_out = {"is_completed": True, "final_answer": "Result is correct."}
            else:
                json_out = {"tool_name": "sum_tool", "args": {"a": 10, "b": 20}, "thought": "Thinking..."}
        elif "steps" in prompt:
            tool_name = "evaluate_branch" if "Explore 3 possible branches" in prompt else "get_data"
            json_out = {
                "steps": [
                    {"tool_name": tool_name, "args": {"query": "run"}, "thought": "Macro step 1"}
                ]
            }
        return {
            "text": text_out,
            "json_data": json_out,
            "model_used": target_model or "google/gemini-2.5-flash",
            "cost": 0.0005
        }
    with patch("app.core.agents.governance.ModelRouter.generate", mock_generate_resp):
        yield

@pytest.fixture(autouse=True)
def clean_registries():
    ToolRegistry.clear()
    PromptRegistry._templates.clear()
    yield
    ToolRegistry.clear()
    PromptRegistry._templates.clear()

@pytest.mark.anyio
async def test_agent_kernel_reasoning_loop():
    # Setup tools
    async def sum_handler(args, context):
        return args["a"] + args["b"]

    tool_meta = ToolMetadata(
        name="sum_tool",
        description="Adds two numbers",
        input_schema={"required": ["a", "b"]},
        permissions=["math:calc"]
    )
    ToolRegistry.register_tool(NativeTool(metadata=tool_meta, handler=sum_handler))

    # Setup Planners and Memory
    model_router = ModelRouter()
    planner = ReActPlanner(model_router=model_router)
    memory_layer = MemoryLayer()
    
    # Pre-populate working memory with a start check
    await memory_layer.working_memory.add_observation("Starting task")

    kernel = AgentKernel(
        planner=planner,
        tool_executor=ToolExecutor(),
        memory_layer=memory_layer,
        knowledge_layer=None,
        policy=PlanningPolicy(max_iterations=3)
    )

    context = AgentContext(
        session_id="session-react-1",
        agent_id="agent-1",
        tenant_id="tenant-1",
        permissions=["math:calc"]
    )

    # Run kernel reasoning loop
    result = await kernel.run(goal="Add 10 and 20", context=context)

    assert result["status"] == "completed"
    assert result["iterations"] >= 1
    assert "Result is correct." in result["final_answer"]
    
    # Check working memory observations
    observations = await memory_layer.working_memory.get_observations()
    assert len(observations) > 0


@pytest.mark.anyio
async def test_all_planners():
    model_router = ModelRouter()
    context = AgentContext(session_id="s1", agent_id="a1", tenant_id="t1")
    memory_layer = MemoryLayer()

    # 1. SequentialPlanner
    seq_planner = SequentialPlanner(model_router=model_router)
    plan = Plan()
    res1 = await seq_planner.plan("Goal", context, memory_layer, PlanningPolicy(), plan)
    assert len(res1.steps) > 0
    assert res1.steps[0].tool_name == "get_data"

    # 2. PlanAndSolvePlanner
    pas_planner = PlanAndSolvePlanner(model_router=model_router)
    res2 = await pas_planner.plan("Goal", context, memory_layer, PlanningPolicy(), plan)
    assert len(res2.steps) > 0
    assert "Macro step 1" in res2.steps[0].thought

    # 3. TreeOfThoughtPlanner
    tot_planner = TreeOfThoughtPlanner(model_router=model_router)
    res3 = await tot_planner.plan("Goal", context, memory_layer, PlanningPolicy(), plan)
    assert len(res3.steps) == 1
    assert res3.steps[0].tool_name == "evaluate_branch"


@pytest.mark.anyio
async def test_memory_layer_and_providers():
    memory = LocalInMemoryMemory()
    await memory.add_concept("c1", "Deep learning algorithms", [1.0, 0.0, 0.0])
    await memory.add_concept("c2", "Web server configurations", [0.0, 1.0, 0.0])

    # Query concepts using semantic cosine similarity
    res1 = await memory.query_concepts([0.9, 0.1, 0.0], limit=1)
    assert len(res1) == 1
    assert res1[0].key == "c1"

    # Coordinates working / episodic / session memory
    layer = MemoryLayer(semantic_provider=memory)
    await layer.save_episode(
        session_id="sess-ep",
        goal="Build engine",
        plan=Plan(steps=[PlanStep(tool_name="tool_1", thought="think")]),
        final_answer="Done"
    )
    
    episodes = await layer.episodic_memory.search_episodes("engine")
    assert len(episodes) == 1
    assert episodes[0].final_answer == "Done"


@pytest.mark.anyio
async def test_knowledge_rag_pipeline():
    knowledge = KnowledgeLayer()
    doc = await knowledge.ingest_document(
        title="Agent Guidelines",
        content="Agents should perform tool capability negotiation before running any native or remote tools."
    )
    assert doc.doc_id in knowledge.documents
    assert len(knowledge.chunks) > 0

    # Retrieve matching chunks with source citation
    results = await knowledge.retrieve("capability negotiation")
    assert len(results) > 0
    assert "negotiation" in results[0].content
    assert results[0].citation.source_title == "Agent Guidelines"
    assert results[0].citation.citation_id.startswith("CIT-")


@pytest.mark.anyio
async def test_governance_safety_and_evaluation():
    router = ModelRouter()
    safety = SafetyPolicy(blocked_keywords=["exploit", "malware"])
    eval_layer = EvaluationLayer(router=router, safety_policy=safety)

    # Verify safety policy block on prompt input
    with pytest.raises(ValueError, match="Prompt blocked by Safety Policy"):
        await eval_layer.generate_and_evaluate(prompt="How to write a malware exploit?")

    # Verify prompt templates
    tpl = PromptTemplate(template_id="t1", template_str="Hello {name}!")
    PromptRegistry.register(tpl)
    retrieved = PromptRegistry.get_template("t1")
    assert retrieved.render({"name": "Fluxa"}) == "Hello Fluxa!"

    # Verify structured output evaluation and fallback/retry
    # Let's request specific JSON keys
    res = await eval_layer.generate_and_evaluate(
        prompt="Output the steps",
        required_keys=["steps"]
    )
    assert "steps" in res["json_data"]


@pytest.mark.anyio
async def test_unified_capability_system():
    # Register a node
    from app.core.registry.node_registry import NodeRegistry, NodeManifest, NodeCapabilities
    from app.core.nodes.node_executor import BaseNodeExecutor

    class DummyExecutor(BaseNodeExecutor):
        async def execute(self, node_data, context, state, services):
            return None

    manifest = NodeManifest(
        id="unique_math_node",
        version="1.0",
        author="official",
        category="math",
        capabilities=NodeCapabilities(),
        permissions=["math:calc"]
    )
    NodeRegistry.register(manifest, DummyExecutor)

    # Retrieve entities satisfying specific capability
    entities = UnifiedCapabilitySystem.find_satisfying_entities("math:calc")
    assert len(entities) >= 1
    assert entities[0].identifier == "unique_math_node"
    assert entities[0].source_type == "node"


def test_skills_package():
    manifest = SkillManifest(
        name="writer_skill",
        version="1.0.0",
        description="Draft blog posts",
        author="editor",
        tools=[]
    )
    skill = SkillPackage(manifest=manifest, templates={"draft": "Drafting topic {topic}"})
    assert skill.list_capabilities() == ["skill:writer_skill"]
    assert skill.get_prompt_template("draft") == "Drafting topic {topic}"
