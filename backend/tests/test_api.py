import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json
from datetime import datetime

from src.api.main import app
from src.database.models import User, Task
from tests.conftest import test_db_session, test_user_data

class TestAPIAuth:
    """Test authentication endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_register_endpoint(self, client, test_db_session):
        """Test user registration"""
        with patch('src.api.main.get_db', return_value=test_db_session):
            response = client.post("/api/register", json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
    
    def test_register_existing_user(self, client, test_db_session, test_user_data):
        """Test registration with existing email"""
        # Create user first
        user = User(**test_user_data)
        test_db_session.add(user)
        test_db_session.commit()
        
        with patch('src.api.main.get_db', return_value=test_db_session):
            response = client.post("/api/register", json={
                "email": test_user_data["email"],
                "password": "password123",
                "name": "Another User"
            })
            
            assert response.status_code == 400
            assert "User already exists" in response.json()["detail"]
    
    def test_login_endpoint(self, client, test_db_session, test_user_data):
        """Test user login"""
        # Create user with hashed password
        from src.utils.auth import AuthHandler
        auth_handler = AuthHandler()
        
        user_data = test_user_data.copy()
        user_data["hashed_password"] = auth_handler.get_password_hash(user_data["password"])
        del user_data["password"]
        
        user = User(**user_data)
        test_db_session.add(user)
        test_db_session.commit()
        
        with patch('src.api.main.get_db', return_value=test_db_session):
            response = client.post("/api/login", json={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
    
    def test_login_invalid_credentials(self, client, test_db_session):
        """Test login with invalid credentials"""
        with patch('src.api.main.get_db', return_value=test_db_session):
            response = client.post("/api/login", json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            })
            
            assert response.status_code == 401
            assert "Invalid credentials" in response.json()["detail"]

class TestAPITasks:
    """Test task-related endpoints"""
    
    @pytest.fixture
    def authenticated_client(self, client, test_db_session, test_user_data):
        """Create authenticated test client"""
        from src.utils.auth import AuthHandler
        auth_handler = AuthHandler()
        
        # Create user
        user_data = test_user_data.copy()
        user_data["hashed_password"] = auth_handler.get_password_hash(user_data["password"])
        del user_data["password"]
        
        user = User(**user_data)
        test_db_session.add(user)
        test_db_session.commit()
        
        # Get token
        token = auth_handler.encode_token(user.id)
        
        # Mock get_db dependency
        async def override_get_db():
            yield test_db_session
        
        app.dependency_overrides[app.dependency_overrides.get('get_db') or 'get_db'] = override_get_db
        
        # Mock get_current_user
        async def override_get_current_user():
            return {"user_id": user.id, "email": user.email}
        
        app.dependency_overrides['get_current_user'] = override_get_current_user
        
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client
    
    def test_submit_task(self, authenticated_client):
        """Test task submission"""
        with patch('src.api.main.get_orchestrator') as mock_orchestrator:
            mock_orchestrator.return_value.submit_task = AsyncMock(
                return_value="test-task-id-123"
            )
            
            response = authenticated_client.post("/api/tasks", json={
                "input_text": "Test task description",
                "priority": "medium",
                "metadata": {"category": "test"},
                "device_info": {"platform": "test"}
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-task-id-123"
            assert data["status"] == "accepted"
    
    def test_get_task_status(self, authenticated_client):
        """Test getting task status"""
        with patch('src.api.main.get_orchestrator') as mock_orchestrator:
            mock_orchestrator.return_value.get_task_status = AsyncMock(
                return_value={
                    "task_id": "test-task-1",
                    "status": "completed",
                    "input": "Test task",
                    "result": {"summary": "Test result"}
                }
            )
            
            response = authenticated_client.get("/api/tasks/test-task-1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-task-1"
            assert data["status"] == "completed"
    
    def test_list_tasks(self, authenticated_client, test_db_session, test_user_data):
        """Test listing user tasks"""
        # Create test tasks
        user = User(**{k: v for k, v in test_user_data.items() if k != 'password'})
        test_db_session.add(user)
        
        for i in range(5):
            task = Task(
                id=f"task-{i}",
                user_id=user.id,
                input_text=f"Task {i}",
                priority=1,
                status="completed" if i % 2 == 0 else "pending",
                created_at=datetime.utcnow()
            )
            test_db_session.add(task)
        
        test_db_session.commit()
        
        response = authenticated_client.get("/api/tasks?limit=3")
        
        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
        assert len(tasks) == 3  # Due to limit
    
    def test_cancel_task(self, authenticated_client):
        """Test task cancellation"""
        with patch('src.api.main.get_orchestrator') as mock_orchestrator:
            mock_orchestrator.return_value.cancel_task = AsyncMock(
                return_value=True
            )
            
            response = authenticated_client.delete("/api/tasks/test-task-123")
            
            assert response.status_code == 200
            assert "cancelled successfully" in response.json()["message"]
    
    def test_unauthenticated_access(self, client):
        """Test accessing protected endpoints without authentication"""
        endpoints = [
            ("POST", "/api/tasks"),
            ("GET", "/api/tasks/test-id"),
            ("GET", "/api/tasks"),
            ("DELETE", "/api/tasks/test-id")
        ]
        
        for method, endpoint in endpoints:
            if method == "POST":
                response = client.post(endpoint, json={})
            elif method == "GET":
                response = client.get(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401  # Unauthorized

class TestAPIHealth:
    """Test health and system endpoints"""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_system_metrics_unauthorized(self, client):
        """Test system metrics without admin access"""
        response = client.get("/api/system/metrics")
        
        assert response.status_code == 401  # Should require authentication
    
    def test_websocket_endpoint(self, client):
        """Test WebSocket endpoint (basic connection test)"""
        # Note: TestClient doesn't support WebSocket testing directly
        # This is a placeholder for real WebSocket tests
        pass
