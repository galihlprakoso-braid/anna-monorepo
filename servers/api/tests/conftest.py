import os
import pytest
from fastapi.testclient import TestClient

# Set test database URL BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data.core.base import Base
from data.models.task import TaskModel  # Import to register with metadata
from data.core.database import get_db
import data.core.database as db_module

@pytest.fixture(scope="function", autouse=True)
def reset_db_state():
    """Reset database singleton state before each test."""
    db_module._engine = None
    db_module._session_local = None
    yield
    db_module._engine = None
    db_module._session_local = None

@pytest.fixture(scope="function")
def client():
    """Create a test client with test database."""
    # Force create in-memory database
    engine = db_module.get_engine()

    # Create all tables
    Base.metadata.create_all(bind=engine)

    from api.main import app

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    Base.metadata.drop_all(bind=engine)
