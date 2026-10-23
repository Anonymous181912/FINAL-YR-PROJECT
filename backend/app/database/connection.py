from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger("healthcare_system")

client: AsyncIOMotorClient | None = None
db = None


async def connect_to_mongo():
    global client, db
    try:
        client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        db = client[settings.mongodb_db_name]
        await client.admin.command("ping")
        logger.info(f"Connected to MongoDB: {settings.mongodb_db_name}")
    except Exception as exc:
        logger.error(f"Failed to connect to MongoDB: {exc}")
        raise


async def close_mongo_connection():
    global client
    if client is not None:
        client.close()
        logger.info("MongoDB connection closed")


def get_database():
    if db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return db
