import os
from typing import Dict, Any


class PluginGenerator:
    """
    Scaffolds complete custom node, trigger, and extension package plugin skeletons
    following Fluxa repository conventions.
    """
    @classmethod
    def scaffold_node(
        cls,
        target_dir: str,
        name: str,
        category: str = "custom",
        author: str = "Developer"
    ) -> Dict[str, Any]:
        """
        Generate a complete custom node plugin skeleton:
        - __init__.py
        - manifest.yaml
        - README.md
        - executor.py
        - tests/__init__.py
        - tests/test_executor.py
        - examples/__init__.py
        - examples/workflow_example.yaml
        """
        plugin_path = os.path.join(target_dir, name)
        os.makedirs(plugin_path, exist_ok=True)
        os.makedirs(os.path.join(plugin_path, "tests"), exist_ok=True)
        os.makedirs(os.path.join(plugin_path, "examples"), exist_ok=True)

        # 1. __init__.py
        init_content = f'"""Fluxa Custom Node Plugin: {name}"""\nfrom .executor import {name.title().replace("_", "")}Executor\n'
        with open(os.path.join(plugin_path, "__init__.py"), "w", encoding="utf-8") as f:
            f.write(init_content)

        # 2. manifest.yaml
        manifest_content = (
            f"id: {name}\n"
            "version: '1.0.0'\n"
            f"author: {author}\n"
            f"category: {category}\n"
            "capabilities:\n"
            "  supports_retry: true\n"
            "  is_cacheable: false\n"
            "inputs:\n"
            "  input_val: string\n"
            "outputs:\n"
            "  result: string\n"
        )
        with open(os.path.join(plugin_path, "manifest.yaml"), "w", encoding="utf-8") as f:
            f.write(manifest_content)

        # 3. README.md
        readme_content = (
            f"# {name} Node Plugin\n\n"
            f"A custom Fluxa workflow node in category `{category}`.\n\n"
            "## Installation\n"
            "Register this node in your project's `NodeRegistry`.\n\n"
            "## Usage\n"
            "See `examples/workflow_example.yaml` for an example definition.\n"
        )
        with open(os.path.join(plugin_path, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme_content)

        # 4. executor.py
        class_name = name.title().replace("_", "") + "Executor"
        executor_content = (
            "from app.core.nodes.node_executor import BaseNodeExecutor\n"
            "from app.core.execution.context import NodeExecutionResult\n\n\n"
            f"class {class_name}(BaseNodeExecutor):\n"
            '    """Custom executor implementation."""\n'
            "    async def execute(self, node_data, context, state, services):\n"
            "        input_val = node_data.get('inputs', {}).get('input_val', '')\n"
            "        output_res = f'Processed: {input_val}'\n"
            "        return NodeExecutionResult(outputs={'result': output_res})\n"
        )
        with open(os.path.join(plugin_path, "executor.py"), "w", encoding="utf-8") as f:
            f.write(executor_content)

        # 5. tests/__init__.py
        with open(os.path.join(plugin_path, "tests", "__init__.py"), "w", encoding="utf-8") as f:
            f.write("# Unit tests for custom node\n")

        # 6. tests/test_executor.py
        test_content = (
            "import pytest\n"
            "from app.core.execution.context import ExecutionState, ExecutionContext\n"
            f"from ..executor import {class_name}\n\n"
            "@pytest.mark.anyio\n"
            f"async def test_{name}_executor():\n"
            f"    executor = {class_name}()\n"
            "    node_data = {'id': 'node_1', 'inputs': {'input_val': 'test'}}\n"
            "    ctx = ExecutionContext(workflow_id='wf_1', execution_id='exec_1', tenant_id='t_1')\n"
            "    state = ExecutionState()\n"
            "    res = await executor.execute(node_data, ctx, state, None)\n"
            "    assert res.outputs['result'] == 'Processed: test'\n"
        )
        with open(os.path.join(plugin_path, "tests", "test_executor.py"), "w", encoding="utf-8") as f:
            f.write(test_content)

        # 7. examples/__init__.py
        with open(os.path.join(plugin_path, "examples", "__init__.py"), "w", encoding="utf-8") as f:
            f.write("# Examples\n")

        # 8. examples/workflow_example.yaml
        example_content = (
            f"id: sample_{name}_workflow\n"
            f"name: Sample {name} Workflow\n"
            "nodes:\n"
            "  - id: n1\n"
            f"    type: {name}\n"
            "    inputs:\n"
            "      input_val: 'hello world'\n"
            "edges: []\n"
        )
        with open(os.path.join(plugin_path, "examples", "workflow_example.yaml"), "w", encoding="utf-8") as f:
            f.write(example_content)

        return {
            "status": "success",
            "plugin_dir": plugin_path,
            "files": [
                "__init__.py",
                "manifest.yaml",
                "README.md",
                "executor.py",
                "tests/__init__.py",
                "tests/test_executor.py",
                "examples/__init__.py",
                "examples/workflow_example.yaml"
            ]
        }

    @classmethod
    def scaffold_package(cls, target_dir: str, name: str, version: str = "0.1.0") -> Dict[str, Any]:
        """Scaffold an extension package directory structure."""
        pkg_path = os.path.join(target_dir, name)
        os.makedirs(pkg_path, exist_ok=True)
        manifest_content = (
            f"name: {name}\n"
            f"version: '{version}'\n"
            "description: 'Fluxa extension package'\n"
            "author: 'Developer'\n"
            "dependencies: []\n"
        )
        with open(os.path.join(pkg_path, "package.yaml"), "w", encoding="utf-8") as f:
            f.write(manifest_content)
        with open(os.path.join(pkg_path, "README.md"), "w", encoding="utf-8") as f:
            f.write(f"# {name} Package\n\nExtension package version {version}.\n")
        return {"status": "success", "package_dir": pkg_path}
