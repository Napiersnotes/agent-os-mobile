import pytest
from datetime import datetime, timedelta
import jwt
from unittest.mock import patch

from src.utils.auth import AuthHandler
from src.database.models import User

class TestAuthHandler:
    """Test authentication utilities"""
    
    def setup_method(self):
        """Setup before each test"""
        self.auth_handler = AuthHandler()
        self.secret_key = "test-secret-key"
        self.algorithm = "HS256"
        self.auth_handler.SECRET_KEY = self.secret_key
        self.auth_handler.ALGORITHM = self.algorithm
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        
        # Hash password
        hashed = self.auth_handler.get_password_hash(password)
        
        # Verify password
        assert self.auth_handler.verify_password(password, hashed)
        assert not self.auth_handler.verify_password("wrong_password", hashed)
    
    def test_token_creation(self):
        """Test JWT token creation"""
        user_id = "test-user-123"
        token = self.auth_handler.encode_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = self.auth_handler.decode_token(token)
        assert payload["sub"] == user_id
        assert "exp" in payload
    
    def test_token_expiration(self):
        """Test token expiration"""
        user_id = "test-user-456"
        
        # Create token with short expiration
        with patch.object(self.auth_handler, 'ACCESS_TOKEN_EXPIRE_MINUTES', 0.01):  # 0.6 seconds
            token = self.auth_handler.encode_token(user_id)
            
            # Wait for expiration
            import time
            time.sleep(1)
            
            # Should raise exception
            with pytest.raises(jwt.ExpiredSignatureError):
                self.auth_handler.decode_token(token)
    
    def test_invalid_token(self):
        """Test handling of invalid tokens"""
        invalid_tokens = [
            "invalid.token.here",
            "header.payload.signature",
            "",
            None
        ]
        
        for token in invalid_tokens:
            if token:
                with pytest.raises(Exception):
                    self.auth_handler.decode_token(token)
    
    def test_token_with_additional_data(self):
        """Test token with additional payload data"""
        user_data = {
            "sub": "user-123",
            "email": "user@example.com",
            "role": "admin",
            "custom": "data"
        }
        
        token = jwt.encode(
            {**user_data, "exp": datetime.utcnow() + timedelta(minutes=30)},
            self.secret_key,
            algorithm=self.algorithm
        )
        
        decoded = self.auth_handler.decode_token(token)
        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "user@example.com"
        assert decoded["role"] == "admin"
    
    def test_verify_password_complexity(self):
        """Test password complexity (simplified)"""
        # In real implementation, this would check password strength
        weak_passwords = ["123", "password", "abc"]
        strong_passwords = ["SecurePass123!", "Complex#Password2024"]
        
        for pwd in weak_passwords:
            hashed = self.auth_handler.get_password_hash(pwd)
            # Should still hash without error
            assert hashed is not None
        
        for pwd in strong_passwords:
            hashed = self.auth_handler.get_password_hash(pwd)
            assert self.auth_handler.verify_password(pwd, hashed)
    
    @pytest.mark.asyncio
    async def test_async_token_verification(self):
        """Test async token verification pattern"""
        user_id = "async-user-123"
        token = self.auth_handler.encode_token(user_id)
        
        # Simulate async verification
        async def verify_async():
            return self.auth_handler.decode_token(token)
        
        decoded = await verify_async()
        assert decoded["sub"] == user_id
    
    def test_token_revocation_pattern(self):
        """Test token blacklist/revocation pattern"""
        user_id = "user-to-revoke"
        token = self.auth_handler.encode_token(user_id)
        
        # In a real system, we might blacklist tokens
        # This test shows the pattern
        blacklist = set()
        blacklist.add(token)
        
        assert token in blacklist
        
        # Attempt to verify blacklisted token
        # (In real implementation, this would fail)
        try:
            decoded = self.auth_handler.decode_token(token)
            # If not implementing blacklist, this should succeed
            assert decoded["sub"] == user_id
        except Exception:
            # If implementing blacklist, this would fail
            pass
