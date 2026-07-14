from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: AsyncIOMotorClient = None

    @classmethod
    async def connect_db(cls, document_models: list = None):
        if document_models is None:
            document_models = []
        logger.info("Connecting to MongoDB...")
        cls.client = AsyncIOMotorClient(settings.db.mongo_uri)
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
