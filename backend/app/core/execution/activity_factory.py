import logging
from typing import Dict, Any
from app.core.execution.context import ExecutionContext
from app.core.execution.engine import ExecutionEngine
from app.core.database import db_manager

# Ensure models are loaded for database queries inside activities
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution

logger = logging.getLogger("fluxa.activity_factory")

class ActivityFactory:
    """
    Factory to resolve dependencies, setup context, and invoke the ExecutionEngine.
    """

    def __init__(self):
        self.engine = ExecutionEngine()

    async def ensure_db_connected(self):
        """
        Verify database manager is initialized and connected.
        """
        if not db_manager.is_connected:
            logger.info("Activity worker establishing database connection...")
            await db_manager.connect_db(document_models=[
                User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution
            ])

    async def execute_node(self, node_def: Dict[str, Any], context: ExecutionContext) -> ExecutionContext:
        # Resolve dependencies (like MongoDB)
        await self.ensure_db_connected()
        
        # Inject tracing/metrics hooks here in the future
        
        # Execute via the stateless engine
        updated_context = await self.engine.execute_node(node_def, context)
        return updated_context
