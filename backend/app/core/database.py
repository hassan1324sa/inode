from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: AsyncIOMotorClient = None

    @property
    def is_connected(self) -> bool:
        return self.client is not None

    @property
    def db(self):
        if self.client is None:
            raise RuntimeError("Database not connected.")
        return self.client[settings.db.database_name]

    @classmethod
    async def connect_db(cls, document_models: list = None):
        if document_models is None:
            document_models = []
        logger.info("Connecting to MongoDB...")
        cls.client = AsyncIOMotorClient(settings.db.mongo_uri)
        # Patch the client to prevent Beanie 2.1.0 from attempting to call
        # append_metadata on the Motor client (which dynamically returns a Database,
        # leading to TypeError: MotorDatabase object is not callable).
        cls.client.append_metadata = None
        
        await init_beanie(
            database=cls.client[settings.db.database_name],
            document_models=document_models
        )
        logger.info("MongoDB connected and Beanie initialized.")

    @classmethod
    async def close_db(cls):
        if cls.client:
            logger.info("Closing MongoDB connection...")
            cls.client.close()
            logger.info("MongoDB connection closed.")

db_manager = DatabaseManager()
