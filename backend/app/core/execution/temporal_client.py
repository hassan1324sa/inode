import logging
import asyncio
from temporalio.client import Client
from app.core.settings import settings

logger = logging.getLogger("fluxa.temporal_client")

class TemporalClientWrapper:
    """
    Wrapper for connecting to Temporal Server and spawning clients.
    """

    def __init__(self):
        self._client = None

    async def get_client(self) -> Client:
        if self._client is None:
            host = settings.temporal.host
            logger.info(f"Connecting to Temporal Server at {host}...")
            for attempt in range(1, 11):
                try:
                    self._client = await Client.connect(host)
                    logger.info("Connected to Temporal successfully.")
                    break
                except Exception as e:
                    if attempt == 10:
                        logger.error(f"Failed to connect to Temporal after {attempt} attempts: {e}")
                        raise e
                    logger.warning(f"Connection to Temporal failed (attempt {attempt}/10): {e}. Retrying in 2 seconds...")
                    await asyncio.sleep(2)
        return self._client
