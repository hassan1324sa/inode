from typing import Dict, Any
from app.core.nodes.node_executor import BaseNodeExecutor, NodeExecutorRegistry
from app.core.execution.context import ExecutionContext
import datetime
from datetime import timezone

@NodeExecutorRegistry.register("schedule_trigger")
class ScheduleTriggerNodeExecutor(BaseNodeExecutor):
    """
    Schedule trigger node. Graph traversal starts here when executed by the scheduler.
    """
    async def execute(self, node_data: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        node_id = node_data.get("id", "schedule_trigger")
        
        context.node_outputs[node_id] = {
            "status": "triggered",
            "cron": node_data.get("cronExpression", "0 * * * *"),
            "triggered_at": datetime.datetime.now(timezone.utc).isoformat()
        }
        return context
