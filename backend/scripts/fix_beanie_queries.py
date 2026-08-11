import re

file_path = r"c:\Users\Latitude 5480\OneDrive\Desktop\Fluxa\backend\app\api\v1\endpoints.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    (r"User\.find_one\(User\.email == user_data\.email\)", r"User.find_one({\"email\": user_data.email})"),
    (r"User\.find_one\(User\.email == req\.email\)", r"User.find_one({\"email\": req.email})"),
    (r"Organization\.find_one\(Organization\.slug == org_id\)", r"Organization.find_one({\"slug\": org_id})"),
    (r"Organization\.find_one\(Organization\.owner_id == str\(user\.id\)\)", r"Organization.find_one({\"owner_id\": str(user.id)})"),
    (r"Organization\.find_one\(Organization\.slug == \"my-personal-org\"\)", r"Organization.find_one({\"slug\": \"my-personal-org\"})"),
    (r"Organization\.find_one\(Organization\.slug == ctx\.organization_id\)", r"Organization.find_one({\"slug\": ctx.organization_id})"),
    (r"WorkflowVersion\.find_one\(WorkflowVersion\.workflow_id == str\(wf\.id\)\)", r"WorkflowVersion.find_one({\"workflow_id\": str(wf.id)})"),
    (r"Workflow\.find_one\(Workflow\.name == wf_id\)", r"Workflow.find_one({\"name\": wf_id})"),
    (r"Workflow\.find_one\(Workflow\.id == wf_id\)", r"Workflow.find_one({\"_id\": ObjectId(wf_id)})"),
]

for old, new in replacements:
    content = re.sub(old, new, content)

# Multi-line cases
content = re.sub(
    r"WorkflowVersion\.find_one\(\s*WorkflowVersion\.workflow_id == str\(wf\.id\),\s*WorkflowVersion\.version == req\.target_version\s*\)",
    r"WorkflowVersion.find_one({\"workflow_id\": str(wf.id), \"version\": req.target_version})",
    content,
    flags=re.MULTILINE | re.DOTALL
)

content = re.sub(
    r"WorkflowVersion\.find_one\(\s*WorkflowVersion\.workflow_id == str\(wf\.id\),\s*WorkflowVersion\.version == target_version\s*\)",
    r"WorkflowVersion.find_one({\"workflow_id\": str(wf.id), \"version\": target_version})",
    content,
    flags=re.MULTILINE | re.DOTALL
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
