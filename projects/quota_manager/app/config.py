"""Application configuration."""

import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./quota_manager.db")
