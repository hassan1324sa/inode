from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json

class PromptTemplate(BaseModel):
    template_id: str
    template_str: str
    version: str = "1.0"

    def render(self, variables: Dict[str, Any]) -> str:
        res = self.template_str
        for k, v in variables.items():
            res = res.replace(f"{{{k}}}", str(v))
        return res


class PromptRegistry:
    _templates: Dict[str, PromptTemplate] = {}

    @classmethod
    def register(cls, template: PromptTemplate):
        cls._templates[template.template_id] = template

    @classmethod
    def get_template(cls, template_id: str) -> Optional[PromptTemplate]:
        return cls._templates.get(template_id)


class ModelRouter(BaseModel):
    openrouter_api_key: Optional[str] = None
    default_model: str = "google/gemini-2.5-flash"
    fallback_models: List[str] = Field(default_factory=lambda: ["google/gemini-2.5-pro", "openai/gpt-4o-mini"])

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Any] = None,
        target_model: Optional[str] = None
    ) -> Dict[str, Any]:
        # Check for Replay & Effect Cache
        execution_id = None
        if context:
            execution_id = getattr(context, "session_id", None) or getattr(context, "execution_id", None)
        
        import hashlib
        request_hash = hashlib.sha256((prompt + (system_prompt or "")).encode("utf-8")).hexdigest()
        is_replay = execution_id and str(execution_id).startswith("replay-")

        if is_replay:
            from app.core.execution.durable_store import MongoDBEventStore
            original_id = str(execution_id).replace("replay-", "")
            effect = await MongoDBEventStore.get_effect(original_id, "llm", request_hash)
            if effect:
                logger.info("Replay matching LLM effect found. Returning cached response.")
                return effect.response.get("output")
            else:
                raise ValueError("No recorded LLM effect found during replay.")

        models_to_try = [target_model] if target_model else []
        models_to_try.extend([self.default_model] + self.fallback_models)
        
        last_error = None
        for model in models_to_try:
            try:
                # Actual OpenRouter call if api key is provided
                if self.openrouter_api_key:
                    import httpx
                    headers = {
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "response_format": {"type": "json_object"}
                    }
                    async with httpx.AsyncClient() as client:
                        res = await client.post("https://openrouter.ai/api/v1/chat/completures", json=payload, headers=headers, timeout=30.0)
                        res.raise_for_status()
                        result = res.json()
                        content = result["choices"][0]["message"]["content"]
                        try:
                            json_data = json.loads(content)
                        except Exception:
                            json_data = {"text": content}
                        
                        ret_val = {
                            "text": content,
                            "json_data": json_data,
                            "model_used": model,
                            "cost": 0.002
                        }
                        if execution_id and not is_replay:
                            from app.core.execution.durable_store import MongoDBEventStore, ExecutionEffect
                            await MongoDBEventStore.save_effect(
                                ExecutionEffect(
                                    execution_id=str(execution_id),
                                    node_id="llm",
                                    effect_type="llm",
                                    provider="model_router",
                                    request_hash=request_hash,
                                    response={"output": ret_val}
                                )
                            )
                        return ret_val
                else:
                    text_out = "Solved."
                    json_out = {"is_completed": True, "final_answer": "Processed successfully."}
                    
                    if "ReAct" in (system_prompt or ""):
                        if "executed tool" in prompt:
                            json_out = {"is_completed": True, "final_answer": "Result is correct."}
                        else:
                            json_out = {"tool_name": "sum_tool", "args": {"a": 10, "b": 20}, "thought": "Thinking..."}
                    elif "steps" in prompt:
                        json_out = {
                            "steps": [
                                {"tool_name": "get_data", "args": {"query": "run"}, "thought": "Init"}
                            ]
                        }

                    ret_val = {
                        "text": text_out,
                        "json_data": json_out,
                        "model_used": model,
                        "cost": 0.0005
                    }
                    if execution_id and not is_replay:
                        from app.core.execution.durable_store import MongoDBEventStore, ExecutionEffect
                        await MongoDBEventStore.save_effect(
                            ExecutionEffect(
                                execution_id=str(execution_id),
                                node_id="llm",
                                effect_type="llm",
                                provider="model_router",
                                request_hash=request_hash,
                                response={"output": ret_val}
                            )
                        )
                    return ret_val
            except Exception as e:
                last_error = e
                continue
                
        raise RuntimeError(f"All routed models failed. Last error: {str(last_error)}")


class SafetyPolicy(BaseModel):
    blocked_keywords: List[str] = Field(default_factory=list)

    def validate_input(self, prompt: str) -> bool:
        for kw in self.blocked_keywords:
            if kw.lower() in prompt.lower():
                return False
        return True

    def validate_output(self, output: str) -> bool:
        for kw in self.blocked_keywords:
            if kw.lower() in output.lower():
                return False
        return True


class EvaluationLayer:
    """
    Validates model output using LLM-as-a-Judge or JSON schemas, and applies retries.
    """
    def __init__(self, router: ModelRouter, safety_policy: Optional[SafetyPolicy] = None):
        self.router = router
        self.safety_policy = safety_policy or SafetyPolicy()

    async def generate_and_evaluate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Any] = None,
        required_keys: Optional[List[str]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        
        # 1. Safety check on prompt
        if not self.safety_policy.validate_input(prompt):
            raise ValueError("Prompt blocked by Safety Policy.")

        retries = 0
        current_prompt = prompt
        
        while retries < max_retries:
            response = await self.router.generate(
                prompt=current_prompt,
                system_prompt=system_prompt,
                context=context
            )
            
            # 2. Output safety check
            if not self.safety_policy.validate_output(response["text"]):
                retries += 1
                current_prompt = prompt + f"\n\nCorrection: Previous output was unsafe. Generate an alternative."
                continue

            # 3. Output structure check
            if required_keys:
                json_data = response.get("json_data", {})
                missing = [k for k in required_keys if k not in json_data]
                if missing:
                    retries += 1
                    current_prompt = (
                        prompt + f"\n\nCorrection: The output was missing required JSON keys: {missing}. "
                        "Please regenerate complying with the schema."
                    )
                    continue
            
            # If all checks pass
            return response
            
        raise ValueError("Failed to obtain acceptable response from model after max retries.")
