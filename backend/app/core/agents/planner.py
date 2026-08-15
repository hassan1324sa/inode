from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.agents.context import AgentContext
from app.core.agents.kernel import Plan, PlanStep

class PlannerResponse(BaseModel):
    steps: List[PlanStep] = []
    is_completed: bool = False
    final_answer: Optional[str] = None
    cost: float = 0.0

class BasePlanner(ABC):
    def __init__(self, model_router: Optional[Any] = None):
        self.model_router = model_router

    @abstractmethod
    async def plan(
        self,
        goal: str,
        context: AgentContext,
        memory_layer: Any,
        policy: Any,
        current_plan: Plan
    ) -> PlannerResponse:
        pass

class SequentialPlanner(BasePlanner):
    """
    Generates a fixed sequence of steps to solve the goal upfront.
    """
    async def plan(
        self,
        goal: str,
        context: AgentContext,
        memory_layer: Any,
        policy: Any,
        current_plan: Plan
    ) -> PlannerResponse:
        if len(current_plan.steps) > 0:
            # If we already have steps and they are all completed, we finish.
            all_done = all(s.status == "completed" for s in current_plan.steps)
            if all_done:
                # Compile a final answer from results
                results_summary = ", ".join([f"{s.tool_name}: {s.result}" for s in current_plan.steps])
                return PlannerResponse(
                    is_completed=True,
                    final_answer=f"Successfully executed all sequential steps. Summary: {results_summary}"
                )
            return PlannerResponse(is_completed=False)

        # First run: construct prompt and query model router
        prompt = (
            f"Given the goal: '{goal}', please output a sequence of actions. "
            "Respond in JSON format with a list of steps, each having 'tool_name', 'args', and 'thought'."
        )
        
        cost = 0.0
        parsed_steps = []
        if self.model_router:
            # Connect to actual OpenRouter/LLM router
            response = await self.model_router.generate(
                prompt=prompt,
                system_prompt="You are a Sequential Planner.",
                context=context
            )
            cost = response.get("cost", 0.0)
            data = response.get("json_data", {})
            raw_steps = data.get("steps", [])
            for rs in raw_steps:
                parsed_steps.append(
                    PlanStep(
                        tool_name=rs.get("tool_name"),
                        args=rs.get("args", {}),
                        thought=rs.get("thought", "")
                    )
                )
        else:
            # Fallback for testing/default when no LLM is configured
            parsed_steps = [
                PlanStep(tool_name="get_data", args={"query": goal}, thought="Retrieve initial details"),
                PlanStep(tool_name="process_data", args={}, thought="Process retrieved details")
            ]
        
        return PlannerResponse(steps=parsed_steps, cost=cost)


class ReActPlanner(BasePlanner):
    """
    Iterative Thought-Action-Observation loop (Reasoning + Acting).
    """
    async def plan(
        self,
        goal: str,
        context: AgentContext,
        memory_layer: Any,
        policy: Any,
        current_plan: Plan
    ) -> PlannerResponse:
        # Fetch working memory trace (observations of previous steps)
        observations = await memory_layer.working_memory.get_observations()
        
        # Discover and format tool definitions
        from app.core.agents.tools import ToolRegistry
        available_tools_desc = []
        preferred_tools = getattr(policy, "preferred_tools", [])
        for tool_name in preferred_tools:
            tool = ToolRegistry.get_tool(tool_name)
            if tool:
                available_tools_desc.append({
                    "name": tool.metadata.name,
                    "description": tool.metadata.description,
                    "inputs": tool.metadata.input_schema
                })

        tools_formatting = json.dumps(available_tools_desc, indent=2) if available_tools_desc else "No tools available."

        system_prompt = (
            "You are a ReAct agent. You have access to the following tools:\n"
            f"{tools_formatting}\n\n"
            "To use a tool, you must respond with a JSON object containing:\n"
            "{\n"
            '  "tool_name": "the_name_of_the_tool",\n'
            '  "args": { ... },\n'
            '  "thought": "your reasoning step"\n'
            "}\n\n"
            "If you have enough information to solve the goal, respond with:\n"
            "{\n"
            '  "is_completed": true,\n'
            '  "final_answer": "your comprehensive final response"\n'
            "}"
        )

        prompt = (
            f"Goal: {goal}\n"
            f"Previous observations:\n" + "\n".join(observations) + "\n"
            "Decide the NEXT single step to take. Provide 'tool_name', 'args', and 'thought' in the requested JSON format."
        )

        cost = 0.0
        if self.model_router:
            response = await self.model_router.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                context=context
            )
            cost = response.get("cost", 0.0)
            data = response.get("json_data", {})
            if data.get("is_completed"):
                return PlannerResponse(
                    is_completed=True,
                    final_answer=data.get("final_answer", "Solved."),
                    cost=cost
                )
            
            next_step = PlanStep(
                tool_name=data.get("tool_name", "final_tool"),
                args=data.get("args", {}),
                thought=data.get("thought", "Thinking...")
            )
            return PlannerResponse(steps=[next_step], cost=cost)
        else:
            # Mock reasoning loop for verification
            if len(observations) == 0:
                return PlannerResponse(
                    steps=[PlanStep(tool_name="search_web", args={"query": goal}, thought="Search the goal")],
                    cost=0.0
                )
            else:
                return PlannerResponse(
                    is_completed=True,
                    final_answer=f"Solved based on: {observations[-1]}",
                    cost=0.0
                )


class PlanAndSolvePlanner(BasePlanner):
    """
    Formulates a macro plan first, then executes and solves incrementally.
    """
    async def plan(
        self,
        goal: str,
        context: AgentContext,
        memory_layer: Any,
        policy: Any,
        current_plan: Plan
    ) -> PlannerResponse:
        if len(current_plan.steps) == 0:
            # Formulate macro plan
            prompt = f"Create a macro-level plan with steps to solve: '{goal}'"
            cost = 0.0
            if self.model_router:
                res = await self.model_router.generate(prompt=prompt, context=context)
                cost = res.get("cost", 0.0)
                # Parse steps...
            
            macro_steps = [
                PlanStep(tool_name="retrieve_docs", args={"query": goal}, thought="Macro step 1"),
                PlanStep(tool_name="synthesize", args={}, thought="Macro step 2")
            ]
            return PlannerResponse(steps=macro_steps, cost=cost)

        all_done = all(s.status == "completed" for s in current_plan.steps)
        if all_done:
            return PlannerResponse(
                is_completed=True,
                final_answer="PlanAndSolve finished: all macro steps solved."
            )
        return PlannerResponse(is_completed=False)


class TreeOfThoughtPlanner(BasePlanner):
    """
    Explores multiple reasoning paths/branches.
    """
    async def plan(
        self,
        goal: str,
        context: AgentContext,
        memory_layer: Any,
        policy: Any,
        current_plan: Plan
    ) -> PlannerResponse:
        # Simulates exploring 3 branches and choosing the best one
        prompt = f"Explore 3 possible branches to solve '{goal}' and return the steps for the highest scoring branch."
        cost = 0.0
        if self.model_router:
            res = await self.model_router.generate(prompt=prompt, context=context)
            cost = res.get("cost", 0.0)
            
        selected_branch_steps = [
            PlanStep(tool_name="evaluate_branch", args={"branch": "best_path"}, thought="ToT selected branch execution")
        ]
        
        if len(current_plan.steps) > 0 and all(s.status == "completed" for s in current_plan.steps):
            return PlannerResponse(is_completed=True, final_answer="TreeOfThought resolved best branch.")
            
        return PlannerResponse(steps=selected_branch_steps, cost=cost)
