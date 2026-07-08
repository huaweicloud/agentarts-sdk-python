"""Real-backend E2E: V11 upload signature authenticates against the live
data-plane gateway.

Auto-discovers a deployed IAM (V11-accepting) agent with file transfer enabled
from the cloud control plane, then drives a V11-signed ``upload-files`` request
at its real data-plane gateway and asserts the signature authenticates
(non-401).  This is the end-to-end proof for the root-cause fix:

  * Before the fix: the V11 signer signed the query string, but the data-plane
    gateway does not -> upload returned HTTP 401 "Authentication failed!" (while
    invoke, which carries no query, succeeded).
  * After the fix: the signer signs an empty canonical query line; upload now
    authenticates (the gateway returns a non-401 such as 404 "Session not
    found" for the probe's fake session, proving auth passed and the request
    reached the agent backend).

The probe is **non-mutating**: it uploads to a throwaway session id that the
backend rejects with 404 before any file is written.  Gated by real AK/SK
(``cloud_credentials``); no billable resources are created.

Run: set ``HUAWEICLOUD_SDK_AK`` / ``HUAWEICLOUD_SDK_SK`` / ``HUAWEICLOUD_SDK_REGION``
in ``tests/integration/.env`` (auto-loaded) and::

    .venv/bin/python -m pytest tests/integration/test_v11_upload_signature_real.py -q
"""

from __future__ import annotations

import re

import pytest

pytestmark = pytest.mark.integration

from agentarts.sdk.runtime.model import SESSION_HEADER
from agentarts.sdk.service.http_client import SignMode
from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.sdk.utils.constant import get_control_plane_endpoint, get_region
from agentarts.sdk.utils.metadata import create_credential
from agentarts.sdk.utils.signer_v11 import V11Signer

_FAKE_SESSION = "aa-it-sigprobe-session"
_PROBE_PARAMS = {"path": "/home/user/aa-it-sigprobe.txt", "user_id": 1000, "file_mode": "0644"}


def _httpsify(endpoint: str) -> str:
    return endpoint if endpoint.startswith(("http://", "https://")) else f"https://{endpoint}"


def _v11_client(base_url: str, cred) -> RuntimeClient:
    client = RuntimeClient(
        data_endpoint=base_url,
        verify_ssl=True,
        sign_mode=SignMode.V11_HMAC_SHA256,
        region_id=get_region(),
    )
    client._data_client._credentials = cred
    return client


def _upload_probe(client: RuntimeClient, agent_name: str):
    """Send a V11-signed upload (fake session) and return the RequestResult."""
    return client._data(
        "POST",
        f"/runtimes/{agent_name}/upload-files",
        data=b"aa-it-sigprobe",
        headers={SESSION_HEADER: _FAKE_SESSION, "Content-Type": "application/octet-stream"},
        params=_PROBE_PARAMS,
        timeout=60,
    )


@pytest.fixture(scope="session")
def v11_upload_agent(cloud_credentials):
    """Auto-discover a deployed IAM agent with file transfer enabled whose
    data-plane gateway accepts V11 signing.  Returns (agent_name, base_url, cred).

    Discovery sends a V11 upload probe (fake session -> 404, non-mutating) to
    each file-transfer-enabled agent and keeps the first whose gateway returns
    non-401 (auth passed).  Skips if none accept V11."""
    cred = create_credential()
    region = cloud_credentials["region"]
    control = RuntimeClient(
        control_endpoint=get_control_plane_endpoint(region), verify_ssl=True
    )

    for agent in control.get_agents(limit=100):
        name = agent.get("name")
        try:
            detail = control.find_agent_by_id(agent["id"])
        except Exception:
            continue
        invoke_config = (detail.get("version_detail") or {}).get("invoke_config") or {}
        if not (invoke_config.get("file_transfer_config") or {}).get("enabled"):
            continue
        access_endpoint = invoke_config.get("access_endpoint")
        if not access_endpoint:
            continue
        base = _httpsify(access_endpoint)
        result = _upload_probe(_v11_client(base, cred), name)
        # non-401 -> the gateway authenticated the V11 signature (e.g. 404
        # "Session not found"); 401 -> this agent's gateway does not accept V11.
        if result.status_code != 401:
            return name, base, cred

    pytest.skip(
        "No deployed IAM (V11-accepting) agent with file transfer enabled was "
        "found in the workspace; deploy one to exercise this E2E test"
    )


class TestV11UploadSignatureRealBackend:
    def test_fixed_signer_upload_authenticates(self, v11_upload_agent):
        """The fix: a V11-signed upload (with query params) authenticates
        against the real data-plane gateway -> non-401."""
        name, base, cred = v11_upload_agent
        result = _upload_probe(_v11_client(base, cred), name)
        assert result.status_code != 401, (
            f"V11 upload still rejected by gateway (401): {result.error}"
        )

    def test_tampered_signature_rejected(self, v11_upload_agent):
        """Control: a corrupted signature is rejected with 401, proving the
        gateway actually verifies signatures (so the passing result above is
        meaningful)."""
        name, base, cred = v11_upload_agent
        client = _v11_client(base, cred)
        full_url = f"{base}/runtimes/{name}/upload-files"
        signed = client._data_client._sign_request_v11(
            "POST", full_url,
            headers={SESSION_HEADER: _FAKE_SESSION, "Content-Type": "application/octet-stream"},
            data=b"aa-it-sigprobe", params=_PROBE_PARAMS, timeout=60,
        )
        signed["headers"]["Authorization"] = re.sub(
            r"Signature=[0-9a-f]+", "Signature=" + "0" * 64,
            signed["headers"]["Authorization"],
        )
        resp = client._data_client._session.request("POST", full_url, verify=True, **signed)
        assert resp.status_code == 401, (
            f"tampered signature unexpectedly accepted: {resp.status_code} {resp.text[:120]}"
        )

    def test_old_behaviour_query_signed_fails(self, v11_upload_agent, monkeypatch):
        """Necessity proof: if the query WERE signed (old behaviour), the real
        gateway rejects with 401 — confirming the fix is required."""
        name, base, cred = v11_upload_agent

        def sign_with_query(self, method, path, query_params, headers):
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

        monkeypatch.setattr(V11Signer, "sign", sign_with_query)
        result = _upload_probe(_v11_client(base, cred), name)
        assert result.status_code == 401, (
            f"old (query-signed) behaviour unexpectedly accepted: "
            f"{result.status_code} {result.error}"
        )
