import asyncio
import logging
from app.core.execution.engine import run_workflow
from typing import Any

logger = logging.getLogger(__name__)

async def execution_worker(queue: asyncio.Queue, memory_cache: Any):
    logger.info("Background execution worker started.")
    while True:
        try:
            execution_id = await queue.get()
            logger.info(f"Worker picked up execution_id: {execution_id}")
            try:
                await run_workflow(execution_id, memory_cache)
            except asyncio.CancelledError:
                logger.info("Worker task cancelled.")
                raise
            except Exception as e:
                logger.exception(f"Unexpected error running workflow {execution_id}: {e}")
            finally:
                queue.task_done()
        except asyncio.CancelledError:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.exception(f"Worker loop error: {e}")
