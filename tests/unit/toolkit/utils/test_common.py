"""Tests for common utility functions"""


from agentarts.toolkit.utils.common import validate_agent_name


class TestValidateAgentName:
    """Tests for validate_agent_name function"""

    def test_valid_simple_name(self):
        """Test valid simple name like 'ab'"""
        is_valid, error = validate_agent_name("ab")
        assert is_valid is True
        assert error == ""

    def test_valid_name_with_hyphen(self):
        """Test valid name with hyphen"""
        is_valid, error = validate_agent_name("my-agent")
        assert is_valid is True
        assert error == ""

    def test_valid_name_with_digits(self):
        """Test valid name with digits"""
        is_valid, error = validate_agent_name("agent123")
        assert is_valid is True
        assert error == ""

    def test_valid_name_complex(self):
        """Test valid complex name"""
        is_valid, error = validate_agent_name("my-agent-v2")
        assert is_valid is True
        assert error == ""

    def test_valid_name_min_length(self):
        """Test valid name with minimum length (2)"""
        is_valid, error = validate_agent_name("ab")
        assert is_valid is True
        assert error == ""

    def test_valid_name_max_length(self):
        """Test valid name with maximum length (48)"""
        long_name = "a" + "b" * 46 + "c"  # 1 + 46 + 1 = 48
        is_valid, error = validate_agent_name(long_name)
        assert is_valid is True
        assert error == ""

    def test_invalid_empty(self):
        """Test invalid empty name"""
        is_valid, error = validate_agent_name("")
        assert is_valid is False
        assert "required" in error.lower()

    def test_invalid_too_short(self):
        """Test invalid name with length < 2"""
        is_valid, error = validate_agent_name("a")
        assert is_valid is False
        assert "at least 2" in error

    def test_invalid_too_long(self):
        """Test invalid name with length > 48"""
        long_name = "a" + "b" * 48 + "c"  # 50 characters
        is_valid, error = validate_agent_name(long_name)
        assert is_valid is False
        assert "at most 48" in error

    def test_invalid_starts_with_digit(self):
        """Test invalid name starting with digit"""
        is_valid, error = validate_agent_name("1agent")
        assert is_valid is False
        assert "start with lowercase letter" in error

    def test_invalid_starts_with_uppercase(self):
        """Test invalid name starting with uppercase letter"""
        is_valid, error = validate_agent_name("Agent")
        assert is_valid is False
        assert "start with lowercase letter" in error

    def test_invalid_starts_with_hyphen(self):
        """Test invalid name starting with hyphen"""
        is_valid, error = validate_agent_name("-agent")
        assert is_valid is False
        assert "start with lowercase letter" in error

    def test_invalid_ends_with_hyphen(self):
        """Test invalid name ending with hyphen"""
        is_valid, error = validate_agent_name("agent-")
        assert is_valid is False
        assert "end with lowercase letter or digit" in error

    def test_invalid_contains_uppercase(self):
        """Test invalid name containing uppercase"""
        is_valid, error = validate_agent_name("my-Agent")
        assert is_valid is False
        assert "lowercase letters, digits, and hyphens" in error

    def test_invalid_contains_underscore(self):
        """Test invalid name containing underscore"""
        is_valid, error = validate_agent_name("my_agent")
        assert is_valid is False
        assert "lowercase letters, digits, and hyphens" in error

    def test_invalid_contains_space(self):
        """Test invalid name containing space"""
        is_valid, error = validate_agent_name("my agent")
        assert is_valid is False
        assert "lowercase letters, digits, and hyphens" in error

    def test_invalid_contains_special_char(self):
        """Test invalid name containing special character"""
        is_valid, error = validate_agent_name("my@agent")
        assert is_valid is False
        assert "lowercase letters, digits, and hyphens" in error

    def test_invalid_consecutive_hyphens(self):
        """Test invalid name with consecutive hyphens - this is actually valid"""
        is_valid, error = validate_agent_name("my--agent")
        assert is_valid is True
        assert error == ""

    def test_valid_single_character_middle(self):
        """Test valid name with single character between start and end"""
        is_valid, error = validate_agent_name("a-b")
        assert is_valid is True
        assert error == ""
