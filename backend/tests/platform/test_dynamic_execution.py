import pytest
from app.core.execution.context import ExecutionContext
from app.core.services.variables.resolver import VariableResolver
from app.core.services.expressions.evaluator import SafeExpressionEvaluator
from app.core.nodes.implementations.conditional import ConditionalNodeExecutor
from app.core.nodes.implementations.ai_agent import AIAgentNodeExecutor
from unittest.mock import patch, MagicMock

def test_variable_resolver_types():
    context_vars = {
        "current_row": {"name": "Ahmed", "sales": 25000, "is_active": True},
        "variables": {"threshold": 15000}
    }
    node_outs = {
        "ai_node": {"text": "Premium User"}
    }
    
    # 1. Resolve raw integer
    res_sales = VariableResolver.resolve("{{current_row.sales}}", context_vars, node_outs)
    assert res_sales == 25000
    assert isinstance(res_sales, int)
    
    # 2. Resolve raw boolean
    res_bool = VariableResolver.resolve("{{current_row.is_active}}", context_vars, node_outs)
    assert res_bool is True
    
    # 3. Resolve template string
    res_str = VariableResolver.resolve("User: {{current_row.name}} status is {{ai_node.text}}", context_vars, node_outs)
    assert res_str == "User: Ahmed status is Premium User"

def test_safe_expression_evaluator():
    # True assertions
    assert SafeExpressionEvaluator.evaluate("25000 > 15000", {}) is True
    assert SafeExpressionEvaluator.evaluate("15000 == 15000", {}) is True
    assert SafeExpressionEvaluator.evaluate("not False", {}) is True
    assert SafeExpressionEvaluator.evaluate("'admin' == 'admin'", {}) is True
    
    # Rejections & Security checks
    with pytest.raises(ValueError):
        SafeExpressionEvaluator.evaluate("__import__('os').system('clear')", {})

@pytest.mark.anyio
async def test_conditional_node_executor_dynamic():
    context = ExecutionContext(
        execution_id="test-exec",
        workflow_definition_id="wf-1",
        workflow_definition_version=1,
        tenant_id="tenant-1",
        variables={"current_row": {"sales": 25000}}
    )
    
    node_data = {
        "id": "cond-1",
        "type": "conditional",
        "expression": "{{current_row.sales}} > 15000"
    }
    
    executor = ConditionalNodeExecutor()
    updated_context = await executor.execute(node_data, context)
    
    assert updated_context.variables["last_condition_result"] is True
    assert updated_context.node_outputs["cond-1"]["branch"] == "true"

@pytest.mark.anyio
async def test_dynamic_e2e_branching_and_ai_workflow():
    async def mock_llm_handler(prompt, system_prompt, context, target_model=None):
        if "Ahmed" in prompt:
            return {
                "text": "Send Premium Email",
                "json_data": {"is_completed": True, "final_answer": "Send Premium Email"}
            }
        return {"text": "Skip", "json_data": {"is_completed": True, "final_answer": "Skip"}}


    # 2. Build dynamic E2E workflow nodes
    read_excel_node = {
        "id": "read-excel-1",
        "type": "read-excel",
        "file_path": "temp_mock.csv", # will be mocked/skipped or read if exists
        "output_var": "customers"
    }

    # Setup dummy context state simulating customer row loop iteration
    context = ExecutionContext(
        execution_id="exec-e2e-dynamic",
        workflow_definition_id="wf-automation-dynamic",
        workflow_definition_version=1,
        tenant_id="tenant-a",
        variables={
            "current_row": {"name": "Ahmed", "sales": 25000, "email": "ahmed@example.com"},
            "minimum_sales": 15000
        }
    )

    # 3. Dynamic Conditional Node: Evaluates condition referencing variables
    conditional_node = {
        "id": "cond-1",
        "type": "conditional",
        "expression": "{{current_row.sales}} > {{variables.minimum_sales}}"
    }

    # 4. Dynamic AI Agent Node: Prompt references current row name & sales
    ai_agent_node = {
        "id": "ai-1",
        "type": "ai_agent",
        "system_prompt": "Analyze sales value.",
        "prompt": "Evaluate {{current_row.name}} with {{current_row.sales}} sales."
    }

    # Execute flow sequentially to verify state mutation and expression evaluation
    from app.core.execution.engine import ExecutionEngine
    engine = ExecutionEngine()

    # Step 1: Run Conditional Node (Ahmed -> sales 25000 > 15000 -> True)
    context = await engine.execute_node(conditional_node, context)
    assert context.node_outputs["cond-1"]["branch"] == "true"

    # Step 2: Run AI Agent Node (mocking ModelRouter.generate)
    with patch("app.core.agents.governance.ModelRouter.generate", side_effect=mock_llm_handler):
        context = await engine.execute_node(ai_agent_node, context)
        assert "Premium" in context.node_outputs["ai-1"]["text"]
        
        # Step 3: Run Email Node resolving recipient from current_row and body from AI output
        email_node = {
            "id": "email-1",
            "type": "send-email",
            "recipient": "{{current_row.email}}",
            "subject": "Reward Alert for {{current_row.name}}",
            "body": "Your status is: {{ai-1.text}}",
            "smtp_host": "localhost",
            "smtp_port": 1025,
            "username": "sales@fluxa.com"
        }
        
        mock_smtp = MagicMock()
        with patch("smtplib.SMTP", return_value=mock_smtp):
            context = await engine.execute_node(email_node, context)
            assert mock_smtp.sendmail.call_count == 1
            # Check resolved values
            call_args = mock_smtp.sendmail.call_args[0]
            assert call_args[1] == ["ahmed@example.com"]
            assert "Reward Alert for Ahmed" in call_args[2]
            assert "Your status is: Send Premium Email" in call_args[2]

@pytest.mark.anyio
async def test_dynamic_e2e_false_branch_evaluation():
    # Setup context state where condition is False (Mohamed -> sales 8000 < minimum_sales 15000)
    context = ExecutionContext(
        execution_id="exec-e2e-false",
        workflow_definition_id="wf-automation-dynamic",
        workflow_definition_version=1,
        tenant_id="tenant-a",
        variables={
            "current_row": {"name": "Mohamed", "sales": 8000, "email": "mohamed@example.com"},
            "minimum_sales": 15000
        }
    )

    conditional_node = {
        "id": "cond-1",
        "type": "conditional",
        "expression": "{{current_row.sales}} > {{variables.minimum_sales}}"
    }

    from app.core.execution.engine import ExecutionEngine
    engine = ExecutionEngine()

    context = await engine.execute_node(conditional_node, context)
    assert context.node_outputs["cond-1"]["branch"] == "false"
    assert context.variables["last_condition_result"] is False


