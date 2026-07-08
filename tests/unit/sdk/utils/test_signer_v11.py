"""Unit tests for the V11-HMAC-SHA256 signer."""

import re
from types import SimpleNamespace

from agentarts.sdk.utils.signer_v11 import V11Signer


def _signed_headers_from_auth(auth_value: str) -> list[str]:
    """Parse the SignedHeaders list out of an Authorization header value."""
    match = re.search(r"SignedHeaders=([^,]+)", auth_value)
    assert match, f"no SignedHeaders in {auth_value!r}"
    return match.group(1).split(";")


def _signature_from_auth(auth_value: str) -> str:
    match = re.search(r"Signature=([0-9a-f]+)", auth_value)
    assert match, f"no Signature in {auth_value!r}"
    return match.group(1)


def _make_signer() -> V11Signer:
    signer = V11Signer("ak", "sk", "cn-southwest-2")
    # Pin the timestamp so signatures are comparable across calls.
    signer._get_timestamp = lambda: "20260709T120000Z"  # type: ignore[assignment]
    return signer


class TestQueryNotSigned:
    """The data-plane gateway does not sign the query string.  The signer must
    therefore produce a signature that is *independent* of the query params
    (they are still sent on the wire, just not signed).  This is the root cause
    of the IAM upload 401: invoke (no query) authenticated, upload (query
    `path=...`) did not, because the client signed the query while the gateway
    does not."""

    def test_query_does_not_affect_signature(self):
        signer = _make_signer()
        base = {"host": "data.example.com", "x-hw-agentarts-session-id": "s"}
        out_no_q = signer.sign("POST", "/runtimes/a/upload-files", None, dict(base))
        out_with_q = signer.sign(
            "POST", "/runtimes/a/upload-files",
            {"path": "/home/user/test.txt", "user_id": 1000, "file_mode": "0644"},
            dict(base),
        )
        assert _signature_from_auth(out_no_q["Authorization"]) == \
            _signature_from_auth(out_with_q["Authorization"]), (
                "query params must not participate in the V11 signature"
            )

    def test_changing_query_value_does_not_change_signature(self):
        signer = _make_signer()
        base = {"host": "h", "x-hw-agentarts-session-id": "s"}
        a = signer.sign("POST", "/p", {"path": "/a/b"}, dict(base))
        b = signer.sign("POST", "/p", {"path": "/x/y/z"}, dict(base))
        assert _signature_from_auth(a["Authorization"]) == \
            _signature_from_auth(b["Authorization"])

    def test_query_is_still_sent_on_wire(self):
        """The signer does not strip query params from the caller's request —
        it only drops them from the signature.  (The HTTP client still sends
        them.)  Here we assert the signer itself doesn't touch them: it only
        takes ``headers`` and returns updated ``headers``."""
        signer = _make_signer()
        out = signer.sign("POST", "/p", {"path": "/x"}, {"host": "h"})
        # Authorization + x-sdk-date added; no query leakage into headers.
        assert "Authorization" in out
        assert out["x-sdk-date"] == "20260709T120000Z"


class TestSignedHeaders:
    """Headers (including Content-Type) ARE signed — the gateway recomputes
    only the declared SignedHeaders from the values it receives, and does not
    rewrite Content-Type for these requests (verified end-to-end)."""

    def test_content_type_is_signed(self):
        signer = _make_signer()
        out = signer.sign("POST", "/p", None, {"host": "h", "Content-Type": "application/octet-stream"})
        assert "content-type" in _signed_headers_from_auth(out["Authorization"])

    def test_changing_content_type_changes_signature(self):
        signer = _make_signer()
        a = signer.sign("POST", "/p", None, {"host": "h", "Content-Type": "application/octet-stream"})
        b = signer.sign("POST", "/p", None, {"host": "h", "Content-Type": "application/json"})
        assert _signature_from_auth(a["Authorization"]) != \
            _signature_from_auth(b["Authorization"])

    def test_changing_signed_header_changes_signature(self):
        """Guard: a signed header value change MUST change the signature."""
        signer = _make_signer()
        a = signer.sign("POST", "/p", None, {"host": "a.example.com"})
        b = signer.sign("POST", "/p", None, {"host": "b.example.com"})
        assert _signature_from_auth(a["Authorization"]) != \
            _signature_from_auth(b["Authorization"])

    def test_signed_headers_sorted_and_lowercased(self):
        signer = _make_signer()
        # "Host" must be lowercased; the signer also adds "x-sdk-date".
        out = signer.sign("GET", "/p", None, {"Host": "h", "X-Custom-Hdr": "v"})
        assert _signed_headers_from_auth(out["Authorization"]) == [
            "host", "x-custom-hdr", "x-sdk-date"
        ]


class TestSignBasics:
    def test_authorization_format(self):
        out = _make_signer().sign("POST", "/p", None, {"host": "h"})
        auth = out["Authorization"]
        assert auth.startswith("V11-HMAC-SHA256 Credential=ak/20260709/cn-southwest-2/apic")
        assert "SignedHeaders=" in auth
        assert "Signature=" in auth

    def test_adds_x_sdk_date_and_authorization(self):
        out = _make_signer().sign("GET", "/p", None, {"host": "h"})
        assert out["x-sdk-date"] == "20260709T120000Z"
        assert "Authorization" in out

    def test_deterministic_for_same_inputs(self):
        s = _make_signer()
        a = s.sign("POST", "/p", {"a": "1"}, {"host": "h", "Content-Type": "x"})
        b = s.sign("POST", "/p", {"a": "1"}, {"host": "h", "Content-Type": "x"})
        assert a["Authorization"] == b["Authorization"]


class TestCanonicalQueryString:
    """``_canonical_query_string`` is the standard-V11 reference implementation.
    It is **not** used to build the signature (the gateway does not sign the
    query); these tests just pin its reference behaviour."""

    def test_empty_when_no_params(self):
        s = V11Signer("ak", "sk", "cn-southwest-2")
        assert s._canonical_query_string(None) == ""
        assert s._canonical_query_string({}) == ""

    def test_sorts_keys(self):
        s = V11Signer("ak", "sk", "cn-southwest-2")
        assert s._canonical_query_string({"user_id": 1000, "file_mode": "0644"}) == \
            "file_mode=0644&user_id=1000"

    def test_space_and_special_encoded(self):
        s = V11Signer("ak", "sk", "cn-southwest-2")
        assert s._canonical_query_string({"q": "a b&c"}) == "q=a%20b%26c"


class TestSignRequestV11Integration:
    """BaseHTTPClient._sign_request_v11 wires query + content-type through
    correctly: query sent on the wire but not signed; content-type signed."""

    def test_v11_sign_request_query_not_signed_content_type_signed(self):
        from agentarts.sdk.service.http_client import BaseHTTPClient, RequestConfig, SignMode

        client = BaseHTTPClient(
            RequestConfig(base_url="https://data.example.com"),
            open_ak_sk=True,
            sign_mode=SignMode.V11_HMAC_SHA256,
            region_id="cn-southwest-2",
        )
        client._credentials = SimpleNamespace(ak="ak", sk="sk", security_token=None)

        # Sign the same request twice: once with query params, once without.
        base_headers = {
            "x-hw-agentarts-session-id": "sess-1",
            "Content-Type": "application/octet-stream",
        }
        with_q = client._sign_request_v11(
            "POST", "https://data.example.com/runtimes/a/upload-files",
            headers=dict(base_headers), data=b"x",
            params={"path": "/home/user/test.txt", "user_id": 1000},
        )
        without_q = client._sign_request_v11(
            "POST", "https://data.example.com/runtimes/a/upload-files",
            headers=dict(base_headers), data=b"x", params=None,
        )

        # Query params are still passed through to the HTTP client (sent on wire).
        assert with_q["params"] == {"path": "/home/user/test.txt", "user_id": 1000}
        # Content-Type is signed.
        assert "content-type" in _signed_headers_from_auth(with_q["headers"]["Authorization"])
        # Signature is independent of the query (query not signed).
        assert _signature_from_auth(with_q["headers"]["Authorization"]) == \
            _signature_from_auth(without_q["headers"]["Authorization"])
