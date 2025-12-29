"""
Simplified test configuration without SQLAlchemy imports in global scope
"""
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

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
        "task_metadata": json.dumps({"category": "test"}),
        "device_info": json.dumps({"platform": "test"}),
        "created_at": datetime.utcnow()
    }

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('redis.asyncio.Redis') as mock:
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

# NO SQLAlchemy imports at module level - they'll be imported only when needed
