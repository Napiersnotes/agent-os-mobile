import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from datetime import datetime

from src.utils.cache import RedisCache
from src.utils.security import SecurityManager
from src.utils.websocket import ConnectionManager

class TestRedisCache:
    """Test Redis cache utilities"""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test setting and getting cache values"""
        with patch('redis.asyncio.Redis') as mock_redis:
            redis_mock = AsyncMock()
            redis_mock.set = AsyncMock(return_value=True)
            redis_mock.get = AsyncMock(return_value=json.dumps({"test": "data"}).encode())
            mock_redis.return_value = redis_mock
            
            cache = RedisCache()
            await cache.initialize()
            
            # Test set
            result = await cache.set("test_key", {"test": "data"}, ttl=60)
            assert result is True
            
            # Test get
            value = await cache.get("test_key")
            assert value == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test cache deletion"""
        with patch('redis.asyncio.Redis') as mock_redis:
            redis_mock = AsyncMock()
            redis_mock.delete = AsyncMock(return_value=1)
            mock_redis.return_value = redis_mock
            
            cache = RedisCache()
            await cache.initialize()
            
            result = await cache.delete("test_key")
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_cache_exists(self):
        """Test cache existence check"""
        with patch('redis.asyncio.Redis') as mock_redis:
            redis_mock = AsyncMock()
            redis_mock.exists = AsyncMock(return_value=1)
            mock_redis.return_value = redis_mock
            
            cache = RedisCache()
            await cache.initialize()
            
            exists = await cache.exists("test_key")
            assert exists is True
    
    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """Test cache TTL functionality"""
        with patch('redis.asyncio.Redis') as mock_redis:
            redis_mock = AsyncMock()
            redis_mock.expire = AsyncMock(return_value=True)
            mock_redis.return_value = redis_mock
            
            cache = RedisCache()
            await cache.initialize()
            
            result = await cache.set("test_key", "value", ttl=30)
            assert result is True

class TestSecurityManager:
    """Test security utilities"""
    
    def test_sanitize_input(self):
        """Test input sanitization"""
        security = SecurityManager()
        
        test_cases = [
            ("<script>alert('xss')</script>", "alert('xss')"),  # Remove HTML tags
            ("Normal text", "Normal text"),  # No change
            ("   trimmed   ", "trimmed"),  # Trim whitespace
            ("Line1\nLine2", "Line1 Line2"),  # Replace newlines
            ("", ""),  # Empty string
        ]
        
        for input_text, expected in test_cases:
            result = security.sanitize_input(input_text)
            assert result == expected
    
    def test_validate_email(self):
        """Test email validation"""
        security = SecurityManager()
        
        valid_emails = [
            "user@example.com",
            "first.last@company.co.uk",
            "user+tag@example.org"
        ]
        
        invalid_emails = [
            "not-an-email",
            "@no-username.com",
            "user@.com",
            "user@com.",
            ""
        ]
        
        for email in valid_emails:
            assert security.validate_email(email) is True
        
        for email in invalid_emails:
            assert security.validate_email(email) is False
    
    def test_password_strength(self):
        """Test password strength validation"""
        security = SecurityManager()
        
        weak_passwords = [
            "123456",
            "password",
            "abc",
            "short"
        ]
        
        strong_passwords = [
            "SecurePass123!",
            "Complex#Password2024",
            "Very$tr0ngP@ssw0rd"
        ]
        
        for pwd in weak_passwords:
            assert security.validate_password_strength(pwd) is False
        
        for pwd in strong_passwords:
            assert security.validate_password_strength(pwd) is True
    
    def test_rate_limit_key(self):
        """Test rate limit key generation"""
        security = SecurityManager()
        
        client_ip = "192.168.1.1"
        endpoint = "/api/tasks"
        
        key = security.get_rate_limit_key(client_ip, endpoint)
        assert key == "rate_limit:192.168.1.1:/api/tasks"
        
        # Test with user_id
        user_key = security.get_rate_limit_key(client_ip, endpoint, user_id="user123")
        assert user_key == "rate_limit:user123:/api/tasks"

class TestWebSocketManager:
    """Test WebSocket connection manager"""
    
    @pytest.mark.asyncio
    async def test_connection_management(self):
        """Test WebSocket connection management"""
        manager = ConnectionManager()
        
        # Mock WebSocket connections
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        # Connect clients
        await manager.connect(ws1, "client1", "user1")
        await manager.connect(ws2, "client2", "user2")
        
        assert len(manager.active_connections) == 2
        assert "client1" in manager.active_connections
        assert "client2" in manager.active_connections
        
        # Disconnect client
        await manager.disconnect("client1")
        assert "client1" not in manager.active_connections
        assert len(manager.active_connections) == 1
    
    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting messages"""
        manager = ConnectionManager()
        
        # Mock WebSocket connections
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        await manager.connect(ws1, "client1", "user1")
        await manager.connect(ws2, "client2", "user2")
        
        # Test broadcast
        message = {"type": "notification", "text": "Hello"}
        await manager.broadcast(message)
        
        # Verify both clients received message
        assert ws1.send_json.call_count == 1
        assert ws2.send_json.call_count == 1
    
    @pytest.mark.asyncio
    async def test_personal_message(self):
        """Test sending personal messages"""
        manager = ConnectionManager()
        
        # Mock WebSocket connection
        ws = AsyncMock()
        await manager.connect(ws, "client1", "user1")
        
        # Send personal message
        message = {"type": "personal", "text": "Hello User1"}
        await manager.send_personal_message(message, ws)
        
        assert ws.send_json.call_count == 1
        called_message = ws.send_json.call_args[0][0]
        assert called_message["text"] == "Hello User1"
    
    @pytest.mark.asyncio
    async def test_task_subscription(self):
        """Test task subscription functionality"""
        manager = ConnectionManager()
        
        # Mock WebSocket connection
        ws = AsyncMock()
        await manager.connect(ws, "client1", "user1")
        
        # Subscribe to task
        await manager.subscribe_to_task("client1", "task-123")
        
        assert "task-123" in manager.task_subscriptions
        assert manager.task_subscriptions["task-123"] == {"client1"}
        
        # Unsubscribe
        await manager.unsubscribe_from_task("client1", "task-123")
        assert "task-123" not in manager.task_subscriptions or \
               "client1" not in manager.task_subscriptions.get("task-123", set())
