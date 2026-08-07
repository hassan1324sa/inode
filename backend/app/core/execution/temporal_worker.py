import asyncio
import os
import logging
from temporalio.worker import Worker
from app.core.execution.temporal_client import TemporalClientWrapper
from app.core.execution.workflows import WorkflowOrchestrator
from app.core.execution.activities import (
    load_execution_context_activity,
    execute_node_activity,
    resolve_loop_items_activity,
    plan_activity,
    execute_tool_activity
)
from app.core.database import db_manager

# Ensure models are loaded
from app.models.user import User
from app.models.organization import Organization
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.execution import Execution
from app.models.node_execution import NodeExecution

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fluxa.temporal_worker")

async def main():
    logger.info("Initializing database connection for worker...")
    await db_manager.connect_db(document_models=[
        User, Organization, Workflow, WorkflowVersion, Execution, NodeExecution
    ])

    client_wrapper = TemporalClientWrapper()
    client = await client_wrapper.get_client()

    task_queue = os.getenv("TASK_QUEUE", "fluxa-core")
    logger.info(f"Starting Temporal Worker listening to task queue: {task_queue}")

    # Register Workflows and Activities
    activities = [
        load_execution_context_activity,
        execute_node_activity,
        resolve_loop_items_activity,
        plan_activity,
        execute_tool_activity
    ]
    
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[WorkflowOrchestrator],
        activities=activities
    )
    
    logger.info(f"Worker running on queue '{task_queue}'... Press Ctrl+C to stop.")
    try:
        await worker.run()
    finally:
        await db_manager.close_db()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker execution interrupted by user.")
