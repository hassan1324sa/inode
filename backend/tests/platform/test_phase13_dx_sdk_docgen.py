import os
import pytest
from sdk.python.fluxa_sdk import (
    FluxaClient,
    AsyncFluxaClient,
    ApiKeyCredential,
    BearerTokenCredential,
    CustomCredential,
    WorkflowBuilder,
    VersionIncompatibleError,
    validate_server_compatibility,
)
from app.dx.emulator import LocalEmulator, EmulatorRunResult
from app.dx.generator import PluginGenerator
from app.dx.docgen import DocumentationGenerator
from app.cli.main import FluxaCLI


def test_sdk_version_compatibility():
    # Valid versions should succeed
    assert validate_server_compatibility(server_version="1.3.0") is True
    assert validate_server_compatibility(server_version="2.0.0") is True

    # Incompatible server version should raise VersionIncompatibleError
    with pytest.raises(VersionIncompatibleError) as exc_info:
        validate_server_compatibility(server_version="0.9.0", minimum_supported="1.0.0")
    assert "incompatible with server version" in str(exc_info.value)


def test_sdk_credentials():
    api_cred = ApiKeyCredential("test_api_key_123")
    assert api_cred.get_headers() == {"X-API-Key": "test_api_key_123"}

    bearer_cred = BearerTokenCredential("token_abc")
    assert bearer_cred.get_headers() == {"Authorization": "Bearer token_abc"}

    custom_cred = CustomCredential({"X-Custom-Header": "value"})
    assert custom_cred.get_headers() == {"X-Custom-Header": "value"}


def test_fluent_workflow_builder():
    builder = WorkflowBuilder(workflow_id="wf_test", name="Test Flow")
    wf = (
        builder.node("start", "default", inputs={"init": True})
        .node("process", "default", inputs={"val": 10})
        .node("end", "default", inputs={})
        .connect("start", "process", condition="True")
        .connect("process", "end")
        .parallel("start", "process")
        .loop("process", max_iterations=3)
        .build()
    )
    assert wf["id"] == "wf_test"
    assert len(wf["nodes"]) == 3
    assert len(wf["edges"]) == 2
    assert wf["nodes"][0]["parallel_group"] is True
    assert wf["nodes"][1]["loop_config"]["max_iterations"] == 3


@pytest.mark.anyio
async def test_async_sdk_client_local_mode():
    client = AsyncFluxaClient(credential=ApiKeyCredential("dummy"), local_mode=True)
    assert client.get_auth_headers() == {"X-API-Key": "dummy"}
    
    wf = (
        client.workflows.create(workflow_id="async_wf", name="Async WF")
        .node("n1", "default", inputs={"a": 1})
        .node("n2", "default", inputs={"b": 2})
        .connect("n1", "n2")
        .build()
    )
    res = await client.workflows.run(wf)
    assert res.status == "success"
    assert "n1" in res.per_node_execution_time
    assert res.execution_time_ms >= 0.0


@pytest.mark.anyio
async def test_local_emulator_debugging_and_metrics():
    wf_data = {
        "id": "debug_wf",
        "nodes": [
            {"id": "step1", "type": "default", "inputs": {"x": 100}},
            {"id": "step2", "type": "default", "inputs": {"y": 200}},
        ],
        "edges": [{"source": "step1", "target": "step2"}]
    }
    # Test Breakpoints
    emulator = LocalEmulator(breakpoints=["step2"])
    res = await emulator.run(wf_data, inputs={"initial": "val"})
    assert res.status == "paused"  # Paused at breakpoint step2
    assert "step1" in res.node_outputs
    
    # Inspect variable
    assert emulator.inspect_variable("initial") == "val"
    state_dump = emulator.get_execution_state()
    assert state_dump["paused"] is True

    # Resume execution
    emulator.resume()
    res2 = await emulator.step()
    assert res2 is not None
    assert "step2" in res2.per_node_execution_time
    assert res2.execution_graph == {"step1": ["step2"], "step2": []}
    assert res2.memory_usage_mb is not None
    assert res2.cpu_usage_percentage is not None


def test_plugin_generator_skeleton(tmp_path):
    res = PluginGenerator.scaffold_node(
        target_dir=str(tmp_path),
        name="custom_math_node",
        category="math",
        author="Test Engineer"
    )
    assert res["status"] == "success"
    plugin_dir = res["plugin_dir"]
    assert os.path.exists(os.path.join(plugin_dir, "__init__.py"))
    assert os.path.exists(os.path.join(plugin_dir, "manifest.yaml"))
    assert os.path.exists(os.path.join(plugin_dir, "README.md"))
    assert os.path.exists(os.path.join(plugin_dir, "executor.py"))
    assert os.path.exists(os.path.join(plugin_dir, "tests", "test_executor.py"))
    assert os.path.exists(os.path.join(plugin_dir, "examples", "workflow_example.yaml"))


def test_documentation_generator_all_formats():
    md = DocumentationGenerator.generate_markdown()
    assert "Fluxa Node Registry Documentation" in md
    
    html = DocumentationGenerator.generate_html()
    assert "<html>" in html and "</table>" in html
    
    json_str = DocumentationGenerator.generate_json()
    assert '"nodes"' in json_str and '"providers"' in json_str
    
    openapi = DocumentationGenerator.generate_openapi_summary()
    assert '"openapi": "3.0.0"' in openapi
    
    sdk_ref = DocumentationGenerator.generate_sdk_reference()
    assert "FluxaClient" in sdk_ref and "TypeScript SDK" in sdk_ref

    mermaid = DocumentationGenerator.generate_mermaid_diagram({
        "nodes": [{"id": "n1", "type": "llm"}, {"id": "n2", "type": "db"}],
        "edges": [{"source": "n1", "target": "n2"}]
    })
    assert "flowchart TD" in mermaid
    assert "n1 --> n2" in mermaid


def test_cli_dx_commands(tmp_path):
    # Test scaffold
    res = FluxaCLI.scaffold(str(tmp_path), "node", "test_cli_node")
    assert res["status"] == "success"
    
    # Test emulate
    wf_data = {"id": "cli_wf", "nodes": [{"id": "n1", "type": "default"}], "edges": []}
    emul_res = FluxaCLI.emulate(wf_data)
    assert emul_res["status"] == "success"
    
    # Test docgen
    doc_res = FluxaCLI.docgen(str(tmp_path), format="markdown")
    assert doc_res["status"] == "success"
    assert os.path.exists(doc_res["file"])
    
    # Test shell completion
    bash_comp = FluxaCLI.completion("bash")
    assert "complete -W" in bash_comp
    zsh_comp = FluxaCLI.completion("zsh")
    assert "#compdef fluxa" in zsh_comp
