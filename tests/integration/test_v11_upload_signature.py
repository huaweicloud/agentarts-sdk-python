"""Integration test: V11 signature verification end-to-end (local mirror).

Stands up a local HTTP server that implements the *verification* side of the
V11-HMAC-SHA256 signature — mirroring what the real data-plane gateway does —
and drives the real ``RuntimeClient.upload_files`` data-plane path against it
over a real socket (no cloud credentials required).

Pins the root cause of the IAM upload 401:

  * The data-plane gateway does **not** include the query string in the V11
    canonical request (it may inject/rewrite query params en route).  Signing
    the query therefore makes the gateway's recomputation diverge and fails
    verification for any request carrying query params (e.g. upload's
    ``path=...``), while query-less requests (e.g. invoke) succeed.

Cases (all against the local mirror verifier, which uses an empty canonical
query line just like the real gateway):
  1. Fixed signer (query not signed) + upload with query -> 200 (auth passes).
  2. Old behaviour (query signed, forced via monkeypatch) + same upload -> 401
     (proves the fix is necessary).
  3. Tampered signature -> 401 (the verifier actually checks the signature).
  4. invoke (no query) -> 200 (the query fix does not regress invoke).

The real-backend counterpart lives in ``test_v11_upload_signature_real.py``.
"""

from __future__ import annotations

import hmac
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from agentarts.sdk.service.http_client import SignMode
from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.sdk.utils.signer_v11 import V11Signer

AK = "AKTEST"
SK = "SKTEST"
REGION = "cn-southwest-2"


class V11Verifier:
    """Server-side V11 verifier — mirrors the data-plane gateway: the canonical
    request uses an *empty* query line (the query is not signed)."""

    def __init__(self) -> None:
        self.last_signed_headers: list[str] = []

    def verify(self, method: str, raw_path: str, headers_lower: dict[str, str]) -> bool:
        auth = headers_lower.get("authorization", "")
        m_sh = re.search(r"SignedHeaders=([^,]+)", auth)
        m_sig = re.search(r"Signature=([0-9a-f]+)", auth)
        if not m_sh or not m_sig:
            return False
        signed_headers = m_sh.group(1).split(";")
        client_signature = m_sig.group(1)
        self.last_signed_headers = signed_headers

        timestamp = headers_lower.get("x-sdk-date", "")
        parsed = urlparse(raw_path)
        path = parsed.path or "/"

        signer = V11Signer(AK, SK, REGION)
        # Empty canonical query line — the gateway does not sign the query.
        canonical_request = (
            f"{method.upper()}\n"
            f"{signer._canonical_uri(path)}\n"
            f"\n"
            f"{signer._canonical_headers(headers_lower, signed_headers)}\n"
            f"{';'.join(signed_headers)}\n"
            f"UNSIGNED-PAYLOAD"
        )
        string_to_sign = signer._get_string_to_sign(canonical_request, timestamp)
        real_use_secret = signer._get_real_use_secret()
        computed = signer._sign_string_to_sign(real_use_secret, string_to_sign)
        return hmac.compare_digest(computed, client_signature)


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_POST(self):
        verifier: V11Verifier = self.server.verifier  # type: ignore[attr-defined]
        length = int(self.headers.get("Content-Length", "0") or "0")
        self.rfile.read(length) if length else b""
        headers_lower = {k.lower(): v for k, v in self.headers.items()}
        ok = verifier.verify(self.command, self.path, headers_lower)
        payload = b'{"status": "uploaded"}' if ok else b'{"error": "Authentication failed!"}'
        code = 200 if ok else 401
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


@pytest.fixture
def v11_server():
    verifier = V11Verifier()
    server = _Server(("127.0.0.1", 0), _Handler)
    server.verifier = verifier  # type: ignore[attr-defined]
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port, verifier
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _make_client(port: int) -> RuntimeClient:
    client = RuntimeClient(
        data_endpoint=f"http://127.0.0.1:{port}",
        verify_ssl=False,
        sign_mode=SignMode.V11_HMAC_SHA256,
        region_id=REGION,
    )
    client._data_client._credentials = SimpleNamespace(ak=AK, sk=SK, security_token=None)
    return client


def _sign_with_query_signed(self, method, path, query_params, headers):
    """Simulate the OLD (buggy) behaviour: include the query in the canonical
    request.  Used to prove the fix is necessary."""
    timestamp = self._get_timestamp()
    headers["x-sdk-date"] = timestamp
    sh = self._signed_headers(headers)
    canonical_request = (
        f"{method.upper()}\n"
        f"{self._canonical_uri(path)}\n"
        f"{self._canonical_query_string(query_params)}\n"
        f"{self._canonical_headers(headers, sh)}\n"
        f"{';'.join(sh)}\n"
        f"UNSIGNED-PAYLOAD"
    )
    string_to_sign = self._get_string_to_sign(canonical_request, timestamp)
    secret = self._get_real_use_secret()
    signature = self._sign_string_to_sign(secret, string_to_sign)
    headers["Authorization"] = self._get_auth_header_value(sh, signature)
    return headers


UPLOAD_FILES = [{"content": b"hello", "filename": "f.txt"}]


class TestV11UploadSignatureLocalMirror:
    def test_fixed_signer_upload_with_query_verifies(self, v11_server):
        """Fixed signer: query is sent on the wire but not signed -> the
        (empty-query) verifier accepts -> 200."""
        port, _ = v11_server
        result = _make_client(port).upload_files(
            agent_name="myagent", session_id="sess-1",
            files=UPLOAD_FILES, path="/home/user/f.txt",
        )
        assert result["status"] == "uploaded"

    def test_old_behaviour_query_signed_fails(self, v11_server, monkeypatch):
        """Necessity proof: if the query WERE signed (old behaviour), the
        empty-query verifier rejects -> 401."""
        port, _ = v11_server
        monkeypatch.setattr(V11Signer, "sign", _sign_with_query_signed)
        with pytest.raises(RuntimeError, match="HTTP 401"):
            _make_client(port).upload_files(
                agent_name="myagent", session_id="sess-1",
                files=UPLOAD_FILES, path="/home/user/f.txt",
            )

    def test_tampered_signature_rejected(self, v11_server):
        port, _ = v11_server
        client = _make_client(port)
        # Sign correctly, then corrupt the signature before sending.
        full_url = f"http://127.0.0.1:{port}/runtimes/myagent/upload-files"
        signed = client._data_client._sign_request_v11(
            "POST", full_url,
            headers={"x-hw-agentarts-session-id": "sess-1",
                     "Content-Type": "application/octet-stream"},
            data=b"hello",
            params={"path": "/home/user/f.txt"},
        )
        signed["headers"]["Authorization"] = re.sub(
            r"Signature=[0-9a-f]+", "Signature=" + "0" * 64,
            signed["headers"]["Authorization"],
        )
        resp = client._data_client._session.request("POST", full_url, verify=False, **signed)
        assert resp.status_code == 401

    def test_invoke_without_query_verifies(self, v11_server):
        """invoke carries no query params; the query fix must not regress it."""
        port, _ = v11_server
        result = _make_client(port).invoke_agent(
            agent_name="myagent", session_id="sess-1", payload='{"input": "hi"}',
        )
        assert isinstance(result, dict)
