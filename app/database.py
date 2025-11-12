import os
import logging
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError, ConnectionFailure
from dotenv import load_dotenv

load_dotenv()  # loads MONGO_URI from .env

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is required")

try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        tls=True,
        tlsAllowInvalidCertificates=False,
        retryWrites=True,
        w="majority"
    )

    db = client["Codex"]
    user_collection = db["codex_users"]

    client.admin.command("ping")
    logger.info("✓ Successfully connected to MongoDB Atlas (Production Mode)")

except (ServerSelectionTimeoutError, ConnectionFailure, ConfigurationError) as e:
    logger.error(f"✖ MongoDB connection failed: {e}")
    raise SystemExit("Database connection failed. Application stopped.")

except Exception as e:
    logger.error(f"✖ Unexpected MongoDB initialization error: {e}")
    raise SystemExit("Database initialization failed. Application stopped.")
