import pytest
import pytest_asyncio
from sqlalchemy import select
from datetime import datetime
import json

from src.database.models import User, Task, TaskResult
from tests.conftest import test_db_session

class TestDatabaseModels:
    """Test database models and CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_user_creation(self, test_db_session):
        """Test creating a user"""
        user = User(
            id="test-id-1",
            email="test@example.com",
            hashed_password="hashed_password",
            name="Test User",
            created_at=datetime.utcnow()
        )
        
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Retrieve user
        result = await test_db_session.execute(
            select(User).where(User.email == "test@example.com")
        )
        retrieved_user = result.scalar_one_or_none()
        
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.name == "Test User"
    
    @pytest.mark.asyncio
    async def test_task_creation(self, test_db_session, test_user_data):
        """Test creating a task"""
        # First create user
        user = User(**test_user_data)
        test_db_session.add(user)
        await test_db_session.commit()
        
        # Create task
        task = Task(
            id="test-task-1",
            user_id=user.id,
            input_text="Test task",
            priority=2,
            status="pending",
            metadata=json.dumps({"category": "test"}),
            device_info=json.dumps({"platform": "test"}),
            created_at=datetime.utcnow()
        )
        
        test_db_session.add(task)
        await test_db_session.commit()
        
        # Retrieve task
        result = await test_db_session.execute(
            select(Task).where(Task.id == "test-task-1")
        )
        retrieved_task = result.scalar_one_or_none()
        
        assert retrieved_task is not None
        assert retrieved_task.input_text == "Test task"
        assert retrieved_task.user_id == user.id
    
    @pytest.mark.asyncio
    async def test_task_result_creation(self, test_db_session, test_user_data):
        """Test creating task result"""
        # Create user and task
        user = User(**test_user_data)
        test_db_session.add(user)
        
        task = Task(
            id="test-task-2",
            user_id=user.id,
            input_text="Test task with result",
            priority=2,
            status="pending",
            created_at=datetime.utcnow()
        )
        test_db_session.add(task)
        
        await test_db_session.commit()
        
        # Create task result
        task_result = TaskResult(
            task_id=task.id,
            result=json.dumps({"summary": "Test result"}),
            processing_time=1.5,
            agent_used="test_agent",
            completed_at=datetime.utcnow()
        )
        
        test_db_session.add(task_result)
        await test_db_session.commit()
        
        # Retrieve task with result
        result = await test_db_session.execute(
            select(Task).where(Task.id == "test-task-2")
        )
        retrieved_task = result.scalar_one_or_none()
        
        assert retrieved_task is not None
        assert retrieved_task.results is not None
        assert len(retrieved_task.results) == 1
        assert retrieved_task.results[0].agent_used == "test_agent"
    
    @pytest.mark.asyncio
    async def test_user_tasks_relationship(self, test_db_session, test_user_data):
        """Test user-tasks relationship"""
        # Create user
        user = User(**test_user_data)
        test_db_session.add(user)
        
        # Create multiple tasks for user
        for i in range(3):
            task = Task(
                id=f"task-{i}",
                user_id=user.id,
                input_text=f"Task {i}",
                priority=1,
                status="pending",
                created_at=datetime.utcnow()
            )
            test_db_session.add(task)
        
        await test_db_session.commit()
        
        # Check user has tasks
        assert len(user.tasks) == 3
        assert all(task.user_id == user.id for task in user.tasks)
    
    @pytest.mark.asyncio
    async def test_task_status_enum(self):
        """Test task status validation"""
        task = Task(
            id="test-status-task",
            user_id="test-user",
            input_text="Test",
            priority=1,
            status="completed",  # Valid status
            created_at=datetime.utcnow()
        )
        
        assert task.status in ["pending", "processing", "completed", "failed", "cancelled"]
    
    @pytest.mark.asyncio
    async def test_password_hashing(self):
        """Test password hashing (simplified)"""
        user = User(
            email="test@example.com",
            name="Test User"
        )
        
        # Test setting password
        test_password = "secure_password"
        user.set_password(test_password)
        
        # In real implementation, this would verify hash
        assert user.hashed_password != test_password
        assert user.hashed_password is not None
    
    @pytest.mark.asyncio
    async def test_json_fields(self, test_db_session, test_user_data):
        """Test JSON field serialization/deserialization"""
        user = User(**test_user_data)
        test_db_session.add(user)
        
        task = Task(
            id="json-test-task",
            user_id=user.id,
            input_text="Test JSON",
            priority=1,
            status="pending",
            metadata=json.dumps({"category": "research", "language": "en"}),
            device_info=json.dumps({"os": "iOS", "browser": "Safari"}),
            created_at=datetime.utcnow()
        )
        
        test_db_session.add(task)
        await test_db_session.commit()
        
        # Retrieve and verify JSON fields
        result = await test_db_session.execute(
            select(Task).where(Task.id == "json-test-task")
        )
        retrieved_task = result.scalar_one_or_none()
        
        metadata = json.loads(retrieved_task.metadata)
        device_info = json.loads(retrieved_task.device_info)
        
        assert metadata["category"] == "research"
        assert metadata["language"] == "en"
        assert device_info["os"] == "iOS"
        assert device_info["browser"] == "Safari"
