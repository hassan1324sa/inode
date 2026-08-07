from typing import Dict, Any, List
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
from app.core.services.variables.resolver import VariableResolver
from app.core.agents.governance import ModelRouter
from app.core.agents.context import AgentContext
from app.core.agents.kernel import AgentKernel, PlanningPolicy
from app.core.agents.planner import ReActPlanner, SequentialPlanner, PlanAndSolvePlanner, TreeOfThoughtPlanner
from app.core.agents.tools import ToolExecutor
from app.core.agents.memory import MemoryLayer, LocalInMemoryMemory, LocalChromaMemory
from app.core.execution.permissions import PolicyEngine

@NodeExecutorRegistry.register("ai_agent")
class AIAgentNodeExecutor(BaseNodeExecutor):
    """
    Upgraded AI Agent executor that integrates directly with the AgentKernel reasoning loop.
    Supports dynamic memory providers, configurable model routers, planner policies,
    and secure tool registry checking.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "ai_agent")
        
        # 1. Resolve prompt configurations
        system_prompt_raw = node_data.get("system_prompt", "You are a helpful assistant.")
        prompt_raw = node_data.get("prompt", "")
        
        system_prompt = VariableResolver.resolve(system_prompt_raw, context.variables, context.node_outputs)
        prompt = VariableResolver.resolve(prompt_raw, context.variables, context.node_outputs)
        
        # 2. Configure Model Router & Vault Credentials
        model_obj = node_data.get("model")
        target_model = "google/gemini-2.5-flash"
        credential_id = None
        
        if isinstance(model_obj, dict):
            target_model = model_obj.get("model", target_model)
            credential_id = model_obj.get("credential_id") or model_obj.get("credentialId")
        elif isinstance(model_obj, str):
            target_model = model_obj
            credential_id = node_data.get("credentialId") or node_data.get("credential_id")
            
        router = ModelRouter(default_model=target_model)
        
        node_api_key = ""
        if credential_id:
            try:
                from app.core.security.context import SecurityContextHolder, SecurityContext
                if not SecurityContextHolder.get_current_context():
                    SecurityContextHolder.set_context(SecurityContext(
                        organization_id=context.tenant_id or "org-enterprise-01",
                        workspace_id="workspace-1",
                        environment_id="env-1",
                        project_id="proj-1",
                        user_id="system"
                    ))
                from app.core.security.secrets import VaultSecretProvider, SecretRef
                provider = VaultSecretProvider()
                ref = SecretRef(provider="vault", path=credential_id, version="1")
                node_api_key = await provider.get(ref)
            except Exception as e:
                import logging
                logging.getLogger("fluxa.ai_agent").warning(f"Could not retrieve credential '{credential_id}' from Vault: {e}")
                
        if not node_api_key:
            node_api_key = node_data.get("apiKey", "")
            
        if node_api_key:
            router.openrouter_api_key = node_api_key
        else:
            from app.core.settings import settings
            if hasattr(settings, "openrouter") and hasattr(settings.openrouter, "api_key"):
                router.openrouter_api_key = settings.openrouter.api_key
            # If openrouter config is in a database or nested under settings
            elif hasattr(settings, "openrouter_api_key"):
                router.openrouter_api_key = settings.openrouter_api_key
            
        # 3. Choose and configure Planner
        planner_type = node_data.get("planner_type", "react").lower()
        if planner_type == "sequential":
            planner = SequentialPlanner(model_router=router)
        elif planner_type == "plan_and_solve":
            planner = PlanAndSolvePlanner(model_router=router)
        elif planner_type == "tree_of_thought":
            planner = TreeOfThoughtPlanner(model_router=router)
        else:
            planner = ReActPlanner(model_router=router)
            
        # 4. Memory Provider Abstraction Integration
        memory_obj = node_data.get("memory")
        memory_provider_type = "conversation"
        memory_key_raw = "default_key"
        
        if isinstance(memory_obj, dict):
            memory_provider_type = memory_obj.get("provider", "conversation").lower()
            memory_key_raw = memory_obj.get("key", "default_key")
        else:
            memory_provider_type = node_data.get("memoryProvider", "conversation").lower()
            memory_key_raw = node_data.get("memoryKey", "default_key")
            
        if memory_provider_type == "chroma":
            provider = LocalChromaMemory(persist_directory="./chroma_db")
        else:
            provider = LocalInMemoryMemory()
            
        memory_layer = MemoryLayer(semantic_provider=provider)
        
        # Resolve custom Memory Key dynamically (e.g. customer_{{current_row.email}})
        memory_key = VariableResolver.resolve(memory_key_raw, context.variables, context.node_outputs)
        
        # Add initial starting context / memory observation
        await memory_layer.working_memory.add_observation(f"Starting execution under key: {memory_key}")
        await memory_layer.working_memory.add_observation(f"System Prompt: {system_prompt}")
        
        # 5. Tool Registry & Policy Enforcement
        tools_list = node_data.get("tools")
        enabled_tools = []
        if isinstance(tools_list, list):
            for t in tools_list:
                if isinstance(t, dict) and t.get("id"):
                    enabled_tools.append(t.get("id"))
                elif isinstance(t, str):
                    enabled_tools.append(t)
        else:
            enabled_tools_raw = node_data.get("enabledTools", [])
            if isinstance(enabled_tools_raw, str):
                enabled_tools = [t.strip() for t in enabled_tools_raw.split(",") if t.strip()]
            else:
                enabled_tools = enabled_tools_raw
        
        # Context permissions check
        granted_permissions = context.variables.get("permissions", ["*"]) # Default wildcard in test
        agent_context = AgentContext(
            session_id=context.execution_id,
            agent_id=node_id,
            tenant_id=context.tenant_id,
            permissions=granted_permissions
        )
        
        # Validate permissions for each enabled tool using PolicyEngine
        from app.core.agents.tools import ToolRegistry
        for tool_name in enabled_tools:
            tool = ToolRegistry.get_tool(tool_name)
            if tool and tool.metadata.permissions:
                if not PolicyEngine.is_allowed(tool.metadata.permissions, granted_permissions):
                    raise PermissionError(f"Agent unauthorized to use tool: {tool_name}")
                    
        # 6. Initialize Agent Kernel and Run
        policy = PlanningPolicy(max_iterations=5, preferred_tools=enabled_tools)
        kernel = AgentKernel(
            planner=planner,
            tool_executor=ToolExecutor(),
            memory_layer=memory_layer,
            knowledge_layer=None,
            policy=policy
        )
        
        result = await kernel.run(goal=str(prompt), context=agent_context)
        
        # 7. Store final structured outputs in execution context
        context.node_outputs[node_id] = {
            "text": result.get("final_answer") or result.get("reason") or "No output generated",
            "json_data": result,
            "status": result.get("status", "completed")
        }
        
        return context
