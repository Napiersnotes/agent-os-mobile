import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, patch
import json
from datetime import datetime, timedelta

# Import aus aktuellem Verzeichnis
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Versuche, aus verschiedenen möglichen Modulen zu importieren
    from database.models import Base
except ImportError:
    try:
        from models import Base, User, Task, TaskResult
    except ImportError:
        # Fallback: Mock-Modelle für Tests
        from sqlalchemy.ext.declarative import declarative_base
        Base = declarative_base()
        
        # Mock-Klassen definieren
        class User:
            def __init__(self, **kwargs):
                self.id = kwargs.get('id')
                self.email = kwargs.get('email')
                self.hashed_password = kwargs.get('hashed_password')
                self.name = kwargs.get('name')
                self.created_at = kwargs.get('created_at')
        
        class Task:
            def __init__(self, **kwargs):
                self.id = kwargs.get('id')
                self.user_id = kwargs.get('user_id')
                self.input_text = kwargs.get('input_text')
                self.priority = kwargs.get('priority')
                self.status = kwargs.get('status')
                self.metadata = kwargs.get('metadata')
                self.device_info = kwargs.get('device_info')
                self.created_at = kwargs.get('created_at')
                self.results = []
        
        class TaskResult:
            def __init__(self, **kwargs):
                self.task_id = kwargs.get('task_id')
                self.result = kwargs.get('result')
                self.processing_time = kwargs.get('processing_time')
                self.agent_used = kwargs.get('agent_used')
                self.completed_at = kwargs.get('completed_at')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

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
    
    # Create all tables if Base is available
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except:
        pass  # Skip if Base not available
    
    # Create session factory
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create session for test
    async with async_session() as session:
        yield session
    
    # Drop all tables after test
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except:
        pass
    
    await engine.dispose()

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
    with patch('utils.cache.Redis') as mock:
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

@pytest.fixture
def mock_settings():
    """Mock settings"""
    class Settings:
        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        DATABASE_URL = TEST_DATABASE_URL
        REDIS_URL = "redis://localhost:6379/1"
    
    return Settings()
