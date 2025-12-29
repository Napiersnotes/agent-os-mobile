import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, patch
import json
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import Base
from src.config import Settings

# Test Database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create async engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create session for test
    async with async_session() as session:
        yield session
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
def mock_settings():
    """Mock settings for tests"""
    settings = Settings()
    settings.SECRET_KEY = "test-secret-key"
    settings.ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    settings.DATABASE_URL = TEST_DATABASE_URL
    settings.REDIS_URL = "redis://localhost:6379/1"
    return settings

@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "id": "test-user-id-123",
        "email": "test@example.com",
        "name": "Test User",
        "password": "password123",
        "created_at": datetime.utcnow()
    }

@pytest.fixture
def test_task_data():
    """Test task data"""
    return {
        "input_text": "Test task description",
        "priority": 2,
        "status": "pending",
        "metadata": json.dumps({"category": "test"}),
        "device_info": json.dumps({"platform": "test"}),
        "created_at": datetime.utcnow()
    }

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('src.utils.cache.Redis') as mock:
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.set = AsyncMock(return_value=True)
        redis_mock.delete = AsyncMock(return_value=True)
        redis_mock.exists = AsyncMock(return_value=0)
        mock.return_value = redis_mock
        yield redis_mock

@pytest.fixture
def mock_openai():
    """Mock OpenAI client"""
    with patch('openai.AsyncOpenAI') as mock:
        client_mock = AsyncMock()
        client_mock.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content="Test AI response",
                            role="assistant"
                        )
                    )
                ]
            )
        )
        mock.return_value = client_mock
        yield client_mock

@pytest.fixture
def mock_httpx():
    """Mock HTTPX client"""
    with patch('httpx.AsyncClient') as mock:
        client_mock = AsyncMock()
        client_mock.get = AsyncMock(
            return_value=Mock(
                status_code=200,
                text="Mock HTTP response",
                json=AsyncMock(return_value={"result": "test"})
            )
        )
        client_mock.post = AsyncMock(
            return_value=Mock(
                status_code=200,
                json=AsyncMock(return_value={"success": True})
            )
        )
        mock.return_value = client_mock
        yield client_mock
