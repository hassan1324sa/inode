import logging
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
            try:
                self._client = await Client.connect(host)
                logger.info("Connected to Temporal successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to Temporal: {e}")
                raise e
        return self._client
