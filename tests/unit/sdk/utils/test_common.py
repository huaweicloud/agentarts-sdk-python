"""
Unit tests for common utility functions
"""

import pytest
from agentarts.sdk.utils.common import generate_random_string


class TestCommonUtils:
    """Test common utility functions"""
    
    def test_generate_random_string_default_length(self):
        """Test generate_random_string with default length"""
        result = generate_random_string()
        assert isinstance(result, str)
        assert len(result) == 4
    
    def test_generate_random_string_custom_length(self):
        """Test generate_random_string with custom length"""
        length = 8
        result = generate_random_string(length=length)
        assert isinstance(result, str)
        assert len(result) == length
    
    def test_generate_random_string_min_length(self):
        """Test generate_random_string with minimum length"""
        result = generate_random_string(length=4)
        assert isinstance(result, str)
        assert len(result) == 4
    
    def test_generate_random_string_max_length(self):
        """Test generate_random_string with maximum length"""
        result = generate_random_string(length=64)
        assert isinstance(result, str)
        assert len(result) == 64
    
    def test_generate_random_string_invalid_length(self):
        """Test generate_random_string with invalid length"""
        with pytest.raises(ValueError):
            generate_random_string(length=3)
        
        with pytest.raises(ValueError):
            generate_random_string(length=65)
