from typing import Optional
from app.core.triggers.base import BaseTrigger, TriggerRequest, ExecutionRequest

class WebhookTrigger(BaseTrigger):
    """
    Triggers execution based on incoming webhook event.
    """
    def __init__(self, id: str, workflow_id: str, secret_token: Optional[str] = None):
        self.id = id
        self.workflow_id = workflow_id
        self.secret_token = secret_token

    async def validate(self, request: TriggerRequest) -> None:
        if self.secret_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header != f"Bearer {self.secret_token}":
                raise ValueError("Unauthorized trigger request")

    async def create_execution(self, request: TriggerRequest) -> ExecutionRequest:
        return ExecutionRequest(
            workflow_id=self.workflow_id,
            input_data=request.payload
        )

class ScheduleTrigger(BaseTrigger):
    """
    Triggers execution based on calendar schedule.
    """
    def __init__(self, id: str, cron: str, workflow_id: str):
        self.id = id
        self.cron = cron
        self.workflow_id = workflow_id

    async def validate(self, request: TriggerRequest) -> None:
        parts = self.cron.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {self.cron}")

    async def create_execution(self, request: TriggerRequest) -> ExecutionRequest:
        return ExecutionRequest(
            workflow_id=self.workflow_id,
            input_data={
                "scheduled_at": request.payload.get("scheduled_at"),
                "trigger_id": self.id
            }
        )
