"""Unit tests for the V11-HMAC-SHA256 signer."""

from agentarts.sdk.utils.signer_v11 import V11Signer


class TestCanonicalQueryString:
    """Tests for V11Signer._canonical_query_string."""

    def test_empty_when_no_params(self):
        assert V11Signer("ak", "sk", "cn-southwest-2")._canonical_query_string(None) == ""
        assert V11Signer("ak", "sk", "cn-southwest-2")._canonical_query_string({}) == ""

    def test_keeps_slash_unencoded(self):
        """Regression: query values containing '/' (e.g. upload's `path`) must
        keep '/' unencoded to match the data-plane gateway's canonicalisation."""
        signer = V11Signer("ak", "sk", "cn-southwest-2")
        result = signer._canonical_query_string({"path": "/home/user/test.txt"})
        assert result == "path=/home/user/test.txt"

    def test_sorts_keys(self):
        signer = V11Signer("ak", "sk", "cn-southwest-2")
        result = signer._canonical_query_string(
            {"path": "/home/user/test.txt", "user_id": 1000, "file_mode": "0644"}
        )
        assert result == "file_mode=0644&path=/home/user/test.txt&user_id=1000"

    def test_simple_value_unchanged(self):
        """Values without '/' are unaffected by the safe-set change."""
        signer = V11Signer("ak", "sk", "cn-southwest-2")
        assert signer._canonical_query_string({"endpoint": "stream"}) == "endpoint=stream"

    def test_list_value_keeps_slash_unencoded(self):
        signer = V11Signer("ak", "sk", "cn-southwest-2")
        result = signer._canonical_query_string({"k": ["/c", "/a/b"]})
        assert result == "k=/a/b&k=/c"

    def test_space_and_special_encoded(self):
        """Non-'/' special chars are still percent-encoded."""
        signer = V11Signer("ak", "sk", "cn-southwest-2")
        result = signer._canonical_query_string({"q": "a b&c"})
        assert result == "q=a%20b%26c"
