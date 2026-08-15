import pytest
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.core.settings import settings
from app.core.agents.governance import ModelRouter
from app.core.security.context import SecurityContext, SecurityContextHolder
from app.core.security.secrets import VaultSecretProvider, SecretRef
from app.core.execution.context import ExecutionContext
from app.core.nodes.implementations.ai_agent import AIAgentNodeExecutor

@pytest.mark.anyio
async def test_credentials_precedence_and_fail_closed():
    # Setup test variables
    context = ExecutionContext(
        execution_id="test-precedence-exec",
        workflow_definition_id="wf-1",
        workflow_definition_version=1,
        tenant_id="tenant-test-precedence",
        variables={}
    )
    
    # 1. Verify Fail-Closed when no credentials exist anywhere
    orig_api_key = settings.openrouter.api_key
    settings.openrouter.api_key = None
    
    node_data = {
        "id": "ai-test",
        "type": "ai_agent",
        "system_prompt": "You are a help bot",
        "prompt": "Say hello"
    }
    
    executor = AIAgentNodeExecutor()
    
    # Since there are no credentials anywhere, executing should fail or routing should fail-closed
    with pytest.raises(ValueError, match="OpenRouter API key is missing"):
        await executor.execute(node_data, context)
        
    # Restore general setting key
    settings.openrouter.api_key = "sk-or-v1-settings-level-test-key-long"
    
    # 2. Verify priority 3: Fallback from Settings is used when no Node/Tenant credentials exist
    # Let's mock ModelRouter.generate to inspect the key passed to it
    generated_key = None
    async def mock_generate(self, prompt, system_prompt=None, context=None, target_model=None):
        nonlocal generated_key
        # Resolve key
        key = self.openrouter_api_key or settings.openrouter.api_key
        generated_key = key
        return {"text": "Response text", "json_data": {"is_completed": True, "final_answer": "Done"}}
        
    from unittest.mock import patch
    with patch("app.core.agents.governance.ModelRouter.generate", mock_generate):
        await executor.execute(node_data, context)
        assert generated_key == "sk-or-v1-settings-level-test-key-long"
        
    # 3. Verify priority 2: Tenant Credential from Vault takes precedence over Settings
    provider = VaultSecretProvider()
    SecurityContextHolder.set_context(SecurityContext(
        organization_id="tenant-test-precedence",
        workspace_id="workspace-1",
        environment_id="env-1",
        project_id="proj-1",
        user_id="system"
    ))
    
    # Put tenant key in Vault
    await provider.put("openrouter_api_key", "sk-or-v1-tenant-level-vault-key-long")
    
    with patch("app.core.agents.governance.ModelRouter.generate", mock_generate):
        await executor.execute(node_data, context)
        assert generated_key == "sk-or-v1-tenant-level-vault-key-long"
        
    # 4. Verify priority 1: Node Specific Credential from Vault takes precedence over Tenant and Settings
    await provider.put("custom_node_key", "sk-or-v1-node-level-vault-key-long")
    node_data_custom = {
        "id": "ai-test-custom",
        "type": "ai_agent",
        "system_prompt": "You are a help bot",
        "prompt": "Say hello",
        "model": {
            "model": "google/gemini-2.5-flash",
            "credential_id": "custom_node_key"
        }
    }
    
    with patch("app.core.agents.governance.ModelRouter.generate", mock_generate):
        await executor.execute(node_data_custom, context)
        assert generated_key == "sk-or-v1-node-level-vault-key-long"
        
    # Cleanup Context
    SecurityContextHolder.clear_context()
    settings.openrouter.api_key = orig_api_key
