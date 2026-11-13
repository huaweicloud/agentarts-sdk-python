"""Regression coverage for VPC security-group configuration."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
import yaml

from agentarts.sdk.service.runtime_client import RuntimeClient
from agentarts.toolkit.operations.runtime.init import create_config_file
from agentarts.toolkit.utils.runtime.config import AgentArtsConfigList, NetworkConfig, VpcConfig


@pytest.mark.parametrize(
    "groups",
    [
        {"security_group_id": ["sg-demo"]},
        {"security_group_ids": ["sg-demo"]},
        {"security_group_id": ["sg-old"], "security_group_ids": ["sg-demo"]},
    ],
    ids=["legacy", "canonical", "both"],
)
def test_security_groups_use_the_api_key(groups):
    data = {
        "vpc_id": "vpc-demo",
        "subnet_id": "subnet-demo",
        "project_id": "project-demo",
        **groups,
    }
    original = data.copy()
    network = NetworkConfig(network_mode="VPC", vpc_config=data)
    expected = {
        "vpc_id": "vpc-demo",
        "subnet_id": "subnet-demo",
        "security_group_ids": ["sg-demo"],
        "project_id": "project-demo",
    }
    assert network.to_dict() == {"network_mode": "VPC", "vpc_config": expected}
    assert network.vpc_config.model_dump() == expected
    assert network.vpc_config.to_dict() == expected
    assert data == original


@pytest.mark.parametrize("value", [[], None])
def test_canonical_empty_value_takes_precedence(value):
    config = VpcConfig(security_group_id=["sg-old"], security_group_ids=value)
    assert config.security_group_ids == value
    assert "security_group_id" not in config.model_dump()
    assert config.to_dict() == {}


def test_legacy_attribute_reads_and_writes_the_canonical_field():
    config = VpcConfig(security_group_id=["sg-demo"])
    assert config.security_group_id is config.security_group_ids
    config.security_group_id.append("sg-second")
    config.security_group_id = ["sg-replaced"]
    assert config.model_dump(exclude_none=True) == {"security_group_ids": ["sg-replaced"]}


def test_legacy_yaml_round_trip_migrates_the_key(tmp_path):
    path = tmp_path / ".agentarts_config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "default_agent": "demo",
                "agents": {
                    "demo": {
                        "runtime": {
                            "network_config": {
                                "network_mode": "VPC",
                                "vpc_config": {"security_group_id": ["sg-demo"]},
                            }
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    config = AgentArtsConfigList.from_yaml(str(path))
    config.to_yaml(str(path))
    saved = yaml.safe_load(path.read_text(encoding="utf-8"))
    vpc = saved["agents"]["demo"]["runtime"]["network_config"]["vpc_config"]
    assert vpc["security_group_ids"] == ["sg-demo"]
    assert "security_group_id" not in vpc
    reloaded = AgentArtsConfigList.from_yaml(str(path))
    assert reloaded.agents["demo"].runtime.network_config.vpc_config.security_group_ids == [
        "sg-demo"
    ]


def test_init_template_and_public_defaults_use_the_canonical_key(tmp_path):
    create_config_file(tmp_path, "demo", "basic", swr_org="demo-org", swr_repo="demo-repo")
    path = tmp_path / ".agentarts_config.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    network = data["agents"]["demo"]["runtime"]["network_config"]
    assert network["network_mode"] == "PUBLIC"
    assert network["vpc_config"]["security_group_ids"] == []
    assert "security_group_id" not in network["vpc_config"]
    assert NetworkConfig().to_dict() == {
        "network_mode": "PUBLIC",
        "vpc_config": {"security_group_ids": []},
    }


def test_runtime_creation_sends_canonical_security_groups():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append((self.path, payload))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"id":"runtime-demo"}')

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}"
    client = RuntimeClient(control_endpoint=endpoint, data_endpoint=endpoint)
    client._control_client._open_ak_sk = False
    client._control_client._session.trust_env = False
    try:
        network = NetworkConfig(
            network_mode="VPC",
            vpc_config={
                "vpc_id": "00000000-0000-0000-0000-000000000001",
                "subnet_id": "00000000-0000-0000-0000-000000000002",
                "security_group_id": ["00000000-0000-0000-0000-000000000003"],
            },
        )
        assert client.create_agent("demo", network_config=network.to_dict()) == {
            "id": "runtime-demo"
        }
        path, payload = received[0]
        assert path == "/v1/core/runtimes"
        assert payload["network_config"] == {
            "network_mode": "VPC",
            "vpc_config": {
                "vpc_id": "00000000-0000-0000-0000-000000000001",
                "subnet_id": "00000000-0000-0000-0000-000000000002",
                "security_group_ids": ["00000000-0000-0000-0000-000000000003"],
            },
        }
    finally:
        client._control_client.close()
        client._data_client.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
