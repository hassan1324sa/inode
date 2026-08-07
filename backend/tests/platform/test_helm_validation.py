import os
import re

def test_helm_template_brackets_balanced():
    """
    Statically check all Helm templates to ensure Jinja2/Go template tags {{ and }} are balanced.
    """
    chart_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../kubernetes/helm/fluxa/templates"))
    assert os.path.exists(chart_dir), f"Templates directory not found at {chart_dir}"

    for root, _, files in os.walk(chart_dir):
        for file in files:
            if file.endswith(".yaml") or file.endswith(".tpl"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Count openings and closings
                openings = len(re.findall(r"\{\{", content))
                closings = len(re.findall(r"\}\}", content))
                
                assert openings == closings, f"Template {file} has unbalanced brackets: {openings} openings vs {closings} closings"
                
                # Check no dangling double curly braces
                assert not re.search(r"\{\{[^\}]*$", content), f"Template {file} has dangling unclosed brackets"
