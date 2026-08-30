"""Tests for the DSH (DeepSeek Harness) platform adapter and CLI integration.

Hermetic: pnpm/uv never run — the dsh adapter's run_cmd seam is patched with
a fake that records invocations and applies simulated effects (package.json
dep, node_modules, MCP stub on PATH). DSH_HOME and HOME point into tmp_path.
"""

import json
import os
import shutil
from pathlib import Path

import pytest
from agentarts_memory_installer import cli
from agentarts_memory_installer.platforms import PLATFORMS
from agentarts_memory_installer.platforms import dsh as dsh_mod
from agentarts_memory_installer.platforms import get_platform
from agentarts_memory_installer.platforms.dsh import DshPlatform
from agentarts_memory_installer.utils import (
    DSH_MCP_COMMAND,
    DSH_MCP_DEV_SPEC,
    DSH_MCP_SPEC,
    DSH_PACKAGE_NAME,
    DSH_PATCH_MARKER,
    ENV_ACTOR_ID,
    ENV_API_KEY,
    ENV_ASSISTANT_ID,
    ENV_REGION,
    ENV_SPACE_ID,
    InstallerError,
    add,
    dsh_credentials_file,
    dsh_env_file,
    dsh_patch_path,
    dsh_source,
    find,
    list_dsh_profiles,
    merge_dsh_patch,
    strip_dsh_patch,
)

# The exact patch-layer template DSH ships for new profiles.
PATCH_TEMPLATE = (
    "# Your patch layer for this dsh profile, applied after every bundle layer:\n"
    "# a top-level YAML array of loader patch entries (id-targeted config\n"
    "# overrides, disables, and insert lists; `!!js` expressions allowed).\n"
    "[]\n"
)

USER_ENTRY = "- id: telemetry-otel\n  disabled: true\n"


# ── Fixtures and helpers ─────────────────────────────────────────────


@pytest.fixture
def dsh_home(tmp_path, monkeypatch):
    """Isolate HOME (manifest) and DSH_HOME (profiles) under tmp_path."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    dsh = tmp_path / "dsh-home"
    monkeypatch.setenv("DSH_HOME", str(dsh))
    return dsh


@pytest.fixture
def bindir(monkeypatch, tmp_path):
    """A stub directory that REPLACES PATH for pnpm/uv/MCP lookups.

    run_cmd is always faked in these tests, so no real binaries are needed —
    and a fully replaced PATH keeps host-installed pnpm/uv/MCP from leaking
    into "missing executable" scenarios.
    """
    d = tmp_path / "bin"
    d.mkdir()
    monkeypatch.setenv("PATH", str(d))
    return d


def _stub(bindir, name):
    exe = Path(bindir) / name
    exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    exe.chmod(0o755)
    return exe


@pytest.fixture
def pnpm_stub(bindir):
    return _stub(bindir, "pnpm")


@pytest.fixture
def uv_stub(bindir):
    return _stub(bindir, "uv")


@pytest.fixture
def mcp_stub(bindir):
    return _stub(bindir, DSH_MCP_COMMAND)


class FakeRunner:
    """Callable stand-in for utils.run_cmd: records calls, applies effects."""

    def __init__(self, bindir, apply=True):
        self.bindir = Path(bindir)
        self.calls: list[tuple[list[str], str]] = []
        self.apply = apply  # False: exit 0 while nothing happens (verification)

    def __call__(self, args, cwd):
        self.calls.append((list(args), cwd))
        if not self.apply:
            return 0, ""
        if args[:2] == ["pnpm", "add"]:
            pkg_path = Path(cwd) / "package.json"
            pkg = json.loads(pkg_path.read_text()) if pkg_path.exists() else {}
            pkg.setdefault("dependencies", {})[DSH_PACKAGE_NAME] = "0.1.0"
            pkg_path.write_text(json.dumps(pkg, indent=2) + "\n")
            nm = Path(cwd) / "node_modules" / DSH_PACKAGE_NAME
            nm.mkdir(parents=True, exist_ok=True)
            (nm / "package.json").write_text(json.dumps({"name": DSH_PACKAGE_NAME}))
            return 0, ""
        if args[:3] == ["uv", "tool", "install"]:
            _stub(self.bindir, DSH_MCP_COMMAND)
            return 0, ""
        if args[:2] == ["pnpm", "remove"]:
            pkg_path = Path(cwd) / "package.json"
            if pkg_path.exists():
                pkg = json.loads(pkg_path.read_text())
                pkg.get("dependencies", {}).pop(DSH_PACKAGE_NAME, None)
                pkg_path.write_text(json.dumps(pkg, indent=2) + "\n")
            shutil.rmtree(Path(cwd) / "node_modules" / DSH_PACKAGE_NAME, ignore_errors=True)
            return 0, ""
        return 0, ""

    def commands(self) -> list[str]:
        return [" ".join(args) for args, _ in self.calls]


@pytest.fixture
def runner(monkeypatch, bindir):
    fake = FakeRunner(bindir)
    monkeypatch.setattr(dsh_mod, "run_cmd", fake)
    return fake


def make_profile(dsh, name="web", patch=PATCH_TEMPLATE):
    """Create a minimal existing DSH profile."""
    p = Path(dsh) / "profiles" / name
    p.mkdir(parents=True, exist_ok=True)
    (p / "package.json").write_text(
        json.dumps(
            {
                "name": f"dsh-profile-{name}",
                "private": True,
                "dependencies": {},
                "dsh": {"profile": {"bundles": []}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if patch is not None:
        (p / "cordis.patch.yml").write_text(patch, encoding="utf-8")
    return p


def _set_creds(monkeypatch):
    monkeypatch.setenv(ENV_SPACE_ID, "test-space-12345")
    monkeypatch.setenv(ENV_API_KEY, "test-api-key-abcdef-123456")
    monkeypatch.setenv(ENV_ACTOR_ID, "user-42")


# ── Registry and detection ───────────────────────────────────────────


class TestRegistryAndDetect:
    def test_dsh_in_registry(self):
        platform = get_platform("dsh")
        assert isinstance(platform, DshPlatform)
        assert "dsh" in PLATFORMS

    def test_dsh_in_valid_targets(self):
        assert "dsh" in cli.VALID_TARGETS

    def test_detect_true_when_dsh_home_exists(self, dsh_home):
        dsh_home.mkdir(parents=True)
        assert DshPlatform().detect() is True

    def test_detect_false_when_missing(self, dsh_home):
        assert DshPlatform().detect() is False

    def test_fixed_user_level(self):
        assert DshPlatform().fixed_user_level is True


class TestListProfiles:
    def test_lists_only_profile_dirs(self, dsh_home):
        make_profile(dsh_home, "web")
        make_profile(dsh_home, "headless")
        # Not profiles: bare dir, the shared node_modules fallback.
        (Path(dsh_home) / "profiles" / "leftovers").mkdir(parents=True)
        (Path(dsh_home) / "profiles" / "node_modules").mkdir(parents=True)

        assert list_dsh_profiles() == ["headless", "web"]

    def test_empty_when_no_dsh_home(self, dsh_home):
        assert list_dsh_profiles() == []


# ── Patch-layer surgery (pure text) ──────────────────────────────────


class TestPatchSurgery:
    def test_merge_into_template(self, tmp_path):
        p = tmp_path / "cordis.patch.yml"
        p.write_text(PATCH_TEMPLATE, encoding="utf-8")

        assert merge_dsh_patch(str(p)) is True
        text = p.read_text(encoding="utf-8")
        assert DSH_PATCH_MARKER in text
        assert "[]" not in text
        # Template comments preserved in place.
        assert text.startswith("# Your patch layer for this dsh profile")

    def test_merge_idempotent(self, tmp_path):
        p = tmp_path / "cordis.patch.yml"
        p.write_text(PATCH_TEMPLATE, encoding="utf-8")
        merge_dsh_patch(str(p))
        assert merge_dsh_patch(str(p)) is False
        assert p.read_text(encoding="utf-8").count(DSH_PATCH_MARKER) == 1

    def test_merge_creates_missing_file(self, tmp_path):
        p = tmp_path / "cordis.patch.yml"
        assert merge_dsh_patch(str(p)) is True
        text = p.read_text(encoding="utf-8")
        assert DSH_PATCH_MARKER in text

    def test_merge_preserves_user_entries(self, tmp_path):
        p = tmp_path / "cordis.patch.yml"
        p.write_text("# keep me\n" + USER_ENTRY, encoding="utf-8")
        merge_dsh_patch(str(p))
        text = p.read_text(encoding="utf-8")
        assert "# keep me" in text
        assert "telemetry-otel" in text
        assert text.count(DSH_PATCH_MARKER) == 1

    def test_strip_restores_empty_array(self, tmp_path):
        p = tmp_path / "cordis.patch.yml"
        p.write_text(PATCH_TEMPLATE, encoding="utf-8")
        merge_dsh_patch(str(p))

        assert strip_dsh_patch(str(p)) is True
        assert p.read_text(encoding="utf-8") == PATCH_TEMPLATE

    def test_strip_keeps_user_entries(self, tmp_path):
        p = tmp_path / "cordis.patch.yml"
        p.write_text("# keep me\n" + USER_ENTRY, encoding="utf-8")
        merge_dsh_patch(str(p))

        strip_dsh_patch(str(p))
        text = p.read_text(encoding="utf-8")
        assert DSH_PATCH_MARKER not in text
        assert "telemetry-otel" in text
        assert "[]" not in text  # entries remain, no placeholder

    def test_strip_missing_file_noop(self, tmp_path):
        assert strip_dsh_patch(str(tmp_path / "nope.yml")) is False


# ── Install (platform level) ─────────────────────────────────────────


class TestInstall:
    def test_happy_path_registry_spec(self, dsh_home, runner, pnpm_stub, mcp_stub, capsys):
        profile = make_profile(dsh_home)
        result = DshPlatform().install("global", {}, True, profile="web")

        assert result.config_dir == str(profile)
        assert result.config_files == [dsh_patch_path("web")]
        assert result.files == []
        # Registry spec, and no uv call because the MCP was already on PATH.
        assert runner.commands() == ["pnpm add " + DSH_PACKAGE_NAME]
        text = Path(dsh_patch_path("web")).read_text(encoding="utf-8")
        assert DSH_PATCH_MARKER in text

    def test_installs_mcp_via_uv_when_missing(self, dsh_home, runner, pnpm_stub, uv_stub):
        make_profile(dsh_home)
        DshPlatform().install("global", {}, True, profile="web")

        assert "uv tool install " + DSH_MCP_SPEC in runner.commands()

    def test_dev_uses_local_sources(self, dsh_home, runner, pnpm_stub, uv_stub):
        make_profile(dsh_home)
        DshPlatform().install("global", {}, True, profile="web", dev=True)

        assert "pnpm add " + dsh_source() in runner.commands()
        assert "uv tool install " + DSH_MCP_DEV_SPEC in runner.commands()

    def test_requires_profile(self, dsh_home):
        with pytest.raises(InstallerError, match="profile"):
            DshPlatform().install("global", {}, True)

    def test_preflight_missing_pnpm_aborts_before_mutation(self, dsh_home, runner, mcp_stub):
        make_profile(dsh_home)
        before = Path(dsh_patch_path("web")).read_text(encoding="utf-8")

        with pytest.raises(InstallerError, match="pnpm not found"):
            DshPlatform().install("global", {}, True, profile="web")
        assert runner.calls == []
        assert Path(dsh_patch_path("web")).read_text(encoding="utf-8") == before

    def test_preflight_missing_mcp_and_uv_aborts(self, dsh_home, runner, pnpm_stub):
        make_profile(dsh_home)
        before = Path(dsh_patch_path("web")).read_text(encoding="utf-8")

        with pytest.raises(InstallerError, match="uv is unavailable"):
            DshPlatform().install("global", {}, True, profile="web")
        assert runner.calls == []
        assert Path(dsh_patch_path("web")).read_text(encoding="utf-8") == before

    def test_pnpm_failure_aborts_before_patch_write(
        self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch
    ):
        make_profile(dsh_home)
        before = Path(dsh_patch_path("web")).read_text(encoding="utf-8")

        def failing_pnpm(args, cwd):
            if args[:2] != ["pnpm", "add"]:
                return FakeRunner.__call__(runner, args, cwd)
            runner.calls.append((list(args), cwd))
            return 1, "boom"

        monkeypatch.setattr(dsh_mod, "run_cmd", failing_pnpm)
        with pytest.raises(InstallerError, match="pnpm add failed"):
            DshPlatform().install("global", {}, True, profile="web")
        assert Path(dsh_patch_path("web")).read_text(encoding="utf-8") == before

    def test_verification_failure_raises(self, dsh_home, monkeypatch, bindir, pnpm_stub, mcp_stub):
        make_profile(dsh_home)
        runner = FakeRunner(bindir, apply=False)
        monkeypatch.setattr(dsh_mod, "run_cmd", runner)

        with pytest.raises(InstallerError, match="verification failed"):
            DshPlatform().install("global", {}, True, profile="web")

    def test_env_summary_marks_missing_actor(self, dsh_home, runner, pnpm_stub, mcp_stub, capsys):
        make_profile(dsh_home)
        DshPlatform().install("global", {}, True, profile="web")

        out = capsys.readouterr().out
        assert ENV_ACTOR_ID in out
        assert "MISSING" in out

    def test_install_idempotent_single_entry(self, dsh_home, runner, pnpm_stub, mcp_stub):
        make_profile(dsh_home)
        DshPlatform().install("global", {}, True, profile="web")
        DshPlatform().install("global", {}, True, profile="web")

        text = Path(dsh_patch_path("web")).read_text(encoding="utf-8")
        assert text.count(DSH_PATCH_MARKER) == 1


# ── Uninstall (platform level) ───────────────────────────────────────


class TestUninstall:
    def test_removes_dep_and_patch(self, dsh_home, runner, pnpm_stub, mcp_stub, capsys):
        profile = make_profile(dsh_home)
        DshPlatform().install("global", {}, True, profile="web")

        DshPlatform().uninstall({"config_dir": str(profile)})

        text = Path(dsh_patch_path("web")).read_text(encoding="utf-8")
        assert DSH_PATCH_MARKER not in text
        assert text == PATCH_TEMPLATE
        pkg = json.loads((profile / "package.json").read_text(encoding="utf-8"))
        assert DSH_PACKAGE_NAME not in pkg.get("dependencies", {})
        out = capsys.readouterr().out
        assert f"uv tool uninstall {DSH_MCP_SPEC}" in out  # shared-resource note

    def test_no_note_when_other_dsh_installs(self, dsh_home, runner, pnpm_stub, mcp_stub, capsys):
        profile = make_profile(dsh_home)
        make_profile(dsh_home, "headless")
        DshPlatform().install("global", {}, True, profile="web")
        add(
            {
                "platform": "dsh",
                "scope": "global",
                "config_dir": str(dsh_home / "profiles" / "headless"),
            }
        )

        DshPlatform().uninstall({"config_dir": str(profile)})

        assert f"uv tool uninstall {DSH_MCP_SPEC}" not in capsys.readouterr().out

    def test_pnpm_missing_still_strips_patch(self, dsh_home, runner, pnpm_stub, mcp_stub, capsys):
        profile = make_profile(dsh_home)
        DshPlatform().install("global", {}, True, profile="web")

        # pnpm disappears before uninstall; the patch strip must still run.
        Path(pnpm_stub).unlink()
        DshPlatform().uninstall({"config_dir": str(profile)})

        out = capsys.readouterr().out
        assert "pnpm not on PATH" in out
        text = Path(dsh_patch_path("web")).read_text(encoding="utf-8")
        assert DSH_PATCH_MARKER not in text


# ── Credential homes: .credentials.yaml + .env ──────────────────────


FULL_CREDS = {
    ENV_API_KEY: "test-api-key-abcdef-123456",
    ENV_SPACE_ID: "test-space-12345",
    ENV_ACTOR_ID: "user-42",
    ENV_ASSISTANT_ID: "deepseek-harness",
    ENV_REGION: "cn-southwest-2",
}

CONFIG_KEYS = (ENV_SPACE_ID, ENV_ACTOR_ID, ENV_ASSISTANT_ID, ENV_REGION)


class TestCredentialHomes:
    def test_install_splits_credential_and_config(self, dsh_home, runner, pnpm_stub, mcp_stub):
        make_profile(dsh_home)

        result = DshPlatform().install("global", dict(FULL_CREDS), True, profile="web")

        # API key → managed credentials store (flat YAML mapping, 0600).
        cred = Path(dsh_credentials_file())
        assert f"{ENV_API_KEY}: {FULL_CREDS[ENV_API_KEY]}\n" in cred.read_text(encoding="utf-8")
        assert cred.stat().st_mode & 0o777 == 0o600
        # The four non-secret keys → user .env; the key must NOT be there.
        env = Path(dsh_env_file())
        env_text = env.read_text(encoding="utf-8")
        assert ENV_API_KEY not in env_text
        for key in CONFIG_KEYS:
            assert f"{key}={FULL_CREDS[key]}" in env_text
        assert env.stat().st_mode & 0o777 == 0o600
        assert str(cred) in result.config_files
        assert str(env) in result.config_files

    def test_install_migrates_key_from_env_file(
        self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch
    ):
        # An older install left the key in .env: a re-run must move it to the
        # managed store and retire the .env line (unrelated keys stay).
        _set_creds(monkeypatch)
        make_profile(dsh_home)
        Path(dsh_env_file()).write_text(
            f"DEEPSEEK_API_KEY=sk-other\n{ENV_API_KEY}=legacy-key-abcdef-123456\n",
            encoding="utf-8",
        )

        assert cli.main(["install", "dsh", "--yes"]) == 0
        env_text = Path(dsh_env_file()).read_text(encoding="utf-8")
        assert ENV_API_KEY not in env_text
        assert "DEEPSEEK_API_KEY=sk-other" in env_text
        cred_text = Path(dsh_credentials_file()).read_text(encoding="utf-8")
        assert f"{ENV_API_KEY}: test-api-key-abcdef-123456" in cred_text

    def test_credentials_store_feeds_install(
        self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch, capsys
    ):
        # Key already in the managed store, four keys in .env: nothing is
        # re-prompted and nothing reads as MISSING.
        for var in FULL_CREDS:
            monkeypatch.delenv(var, raising=False)
        make_profile(dsh_home)
        Path(dsh_credentials_file()).write_text(
            f"{ENV_API_KEY}: {FULL_CREDS[ENV_API_KEY]}\n", encoding="utf-8"
        )
        Path(dsh_env_file()).write_text(
            "".join(f"{k}={v}\n" for k, v in FULL_CREDS.items() if k != ENV_API_KEY),
            encoding="utf-8",
        )

        assert cli.main(["install", "dsh", "--yes"]) == 0
        assert "MISSING" not in capsys.readouterr().out

    def test_process_env_wins_over_files(self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch):
        for var in FULL_CREDS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv(ENV_ACTOR_ID, "from-env")
        monkeypatch.setenv(ENV_API_KEY, "key-from-env-abcdef-123456")
        make_profile(dsh_home)
        Path(dsh_env_file()).write_text(f"{ENV_ACTOR_ID}=from-file\n", encoding="utf-8")
        Path(dsh_credentials_file()).write_text(
            f"{ENV_API_KEY}: key-from-file-abcdef-123456\n", encoding="utf-8"
        )

        assert cli.main(["install", "dsh", "--yes"]) == 0
        assert f"{ENV_ACTOR_ID}=from-env" in Path(dsh_env_file()).read_text(encoding="utf-8")
        cred_text = Path(dsh_credentials_file()).read_text(encoding="utf-8")
        assert f"{ENV_API_KEY}: key-from-env-abcdef-123456" in cred_text

    def test_install_skips_writes_without_creds(self, dsh_home, runner, pnpm_stub, mcp_stub):
        make_profile(dsh_home)

        result = DshPlatform().install("global", {}, True, profile="web")

        assert not Path(dsh_env_file()).exists()
        assert not Path(dsh_credentials_file()).exists()
        assert result.config_files == [dsh_patch_path("web")]

    def test_uninstall_strips_both_files(self, dsh_home, runner, pnpm_stub, mcp_stub, capsys):
        profile = make_profile(dsh_home)
        DshPlatform().install("global", dict(FULL_CREDS), True, profile="web")
        Path(dsh_env_file()).write_text(
            f"DEEPSEEK_API_KEY=sk-other\n{ENV_ACTOR_ID}=user-42\n",
            encoding="utf-8",
        )
        Path(dsh_credentials_file()).write_text(
            f"DEEPSEEK_API_KEY: sk-deep\n{ENV_API_KEY}: test-api-key-abcdef-123456\n",
            encoding="utf-8",
        )

        DshPlatform().uninstall({"config_dir": str(profile)})

        assert Path(dsh_env_file()).read_text(encoding="utf-8") == "DEEPSEEK_API_KEY=sk-other\n"
        assert (
            Path(dsh_credentials_file()).read_text(encoding="utf-8")
            == "DEEPSEEK_API_KEY: sk-deep\n"
        )
        out = capsys.readouterr().out
        assert "left untouched" in out

    def test_uninstall_removes_emptied_credentials_file(
        self, dsh_home, runner, pnpm_stub, mcp_stub
    ):
        profile = make_profile(dsh_home)
        DshPlatform().install("global", dict(FULL_CREDS), True, profile="web")

        DshPlatform().uninstall({"config_dir": str(profile)})

        assert not Path(dsh_credentials_file()).exists()

    def test_dsh_never_offers_shell_rc_persistence(
        self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch
    ):
        _set_creds(monkeypatch)
        make_profile(dsh_home)
        captured = {}
        real = cli.ensure_credentials

        def spy(yes, platform=None, persist_rc=True):
            captured["persist_rc"] = persist_rc
            return real(yes, platform=platform, persist_rc=persist_rc)

        monkeypatch.setattr(cli, "ensure_credentials", spy)
        assert cli.main(["install", "dsh", "--yes"]) == 0
        assert captured["persist_rc"] is False


# ── DSH home selection ───────────────────────────────────────────────


class TestDshHomeSelection:
    def test_install_with_dsh_home_flag(self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch):
        _set_creds(monkeypatch)
        custom = dsh_home.parent / "custom-dsh"
        make_profile(custom)

        assert cli.main(["install", "dsh", "--dsh-home", str(custom), "--yes"]) == 0

        entry = find("dsh")
        assert entry is not None
        assert entry["config_dir"] == str(custom / "profiles" / "web")
        assert entry["dsh_home"] == str(custom)
        patch = (custom / "profiles" / "web" / "cordis.patch.yml").read_text(encoding="utf-8")
        assert DSH_PATCH_MARKER in patch

    def test_install_invalid_dsh_home_errors(
        self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch, capsys
    ):
        _set_creds(monkeypatch)
        rc = cli.main(["install", "dsh", "--dsh-home", str(dsh_home.parent / "nope"), "--yes"])
        assert rc == 1
        assert "DSH home not found" in capsys.readouterr().err

    def test_prompt_defaults_to_autodetected(self, dsh_home, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        seen = {}

        def fake_prompt(prompt, default=""):
            seen["default"] = default
            return default

        monkeypatch.setattr(cli, "prompt_input", fake_prompt)

        assert cli._select_dsh_home(None, yes=False) == str(dsh_home)
        assert seen["default"] == str(dsh_home)
        assert os.environ["DSH_HOME"] == str(dsh_home)

    def test_prompt_accepts_typed_home(self, dsh_home, monkeypatch):
        custom = dsh_home.parent / "typed-home"
        custom.mkdir()
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        monkeypatch.setattr(cli, "prompt_input", lambda prompt, default="": str(custom))

        assert cli._select_dsh_home(None, yes=False) == str(custom)
        assert os.environ["DSH_HOME"] == str(custom)

    def test_typed_home_must_exist(self, dsh_home, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        missing = str(dsh_home.parent / "missing-home")
        monkeypatch.setattr(cli, "prompt_input", lambda prompt, default="": missing)

        with pytest.raises(InstallerError, match="DSH home not found"):
            cli._select_dsh_home(None, yes=False)

    def test_yes_uses_autodetected_silently(self, dsh_home):
        assert cli._select_dsh_home(None, yes=True) == str(dsh_home)

    def test_uninstall_profile_lookup_across_homes(
        self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch
    ):
        # Install recorded under a custom home; current DSH_HOME points elsewhere.
        _set_creds(monkeypatch)
        custom = dsh_home.parent / "custom-dsh"
        profile = make_profile(custom)
        pkg = json.loads((profile / "package.json").read_text(encoding="utf-8"))
        pkg["dependencies"] = {DSH_PACKAGE_NAME: "0.1.0"}
        (profile / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
        add(
            {
                "platform": "dsh",
                "scope": "global",
                "config_dir": str(profile),
                "config_files": [str(profile / "cordis.patch.yml")],
                "profile": "web",
                "dsh_home": str(custom),
            }
        )

        assert cli.main(["uninstall", "dsh", "--profile", "web", "--yes"]) == 0
        patch = (profile / "cordis.patch.yml").read_text(encoding="utf-8")
        assert DSH_PATCH_MARKER not in patch
        assert find("dsh") is None

    def test_uninstall_ambiguous_profile_errors(
        self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch, capsys
    ):
        for name in ("home-a", "home-b"):
            profile = make_profile(dsh_home.parent / name)
            add(
                {
                    "platform": "dsh",
                    "scope": "global",
                    "config_dir": str(profile),
                    "profile": "web",
                    "dsh_home": str(dsh_home.parent / name),
                }
            )

        rc = cli.main(["uninstall", "dsh", "--profile", "web", "--yes"])
        assert rc == 1
        assert "multiple dsh installs" in capsys.readouterr().err

    def test_uninstall_multiple_dsh_without_profile_errors(
        self, dsh_home, runner, pnpm_stub, mcp_stub, monkeypatch, capsys
    ):
        # Two different profiles installed; uninstalling without --profile
        # must fail instead of silently removing the first match.
        for name, profile_name in (("home-a", "web"), ("home-b", "headless")):
            profile = make_profile(dsh_home.parent / name, profile_name)
            add(
                {
                    "platform": "dsh",
                    "scope": "global",
                    "config_dir": str(profile),
                    "profile": profile_name,
                    "dsh_home": str(dsh_home.parent / name),
                }
            )

        rc = cli.main(["uninstall", "dsh", "--yes"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "multiple dsh installs" in err
        assert "--profile" in err
        assert "'web'" in err and "'headless'" in err


# ── CLI end-to-end ───────────────────────────────────────────────────


class TestCliEndToEnd:
    def test_install_and_uninstall_roundtrip(
        self, dsh_home, runner, pnpm_stub, uv_stub, monkeypatch, capsys
    ):
        _set_creds(monkeypatch)
        make_profile(dsh_home)

        assert cli.main(["install", "dsh", "--yes"]) == 0
        entry = find("dsh")
        assert entry is not None
        assert entry["scope"] == "global"  # fixed_user_level
        assert entry["profile"] == "web"
        assert entry["config_dir"] == str(dsh_home / "profiles" / "web")
        assert DSH_PATCH_MARKER in Path(dsh_patch_path("web")).read_text(encoding="utf-8")

        assert cli.main(["uninstall", "dsh", "--profile", "web", "--yes"]) == 0
        assert find("dsh") is None
        assert DSH_PATCH_MARKER not in Path(dsh_patch_path("web")).read_text(encoding="utf-8")

    def test_install_missing_profile_errors(
        self, dsh_home, runner, pnpm_stub, uv_stub, monkeypatch, capsys
    ):
        _set_creds(monkeypatch)
        make_profile(dsh_home)

        rc = cli.main(["install", "dsh", "--profile", "nope", "--yes"])
        assert rc == 1
        assert "not found" in capsys.readouterr().err

    def test_install_no_profiles_errors(self, dsh_home, runner, pnpm_stub, monkeypatch):
        _set_creds(monkeypatch)
        dsh_home.mkdir(parents=True)

        rc = cli.main(["install", "dsh", "--yes"])
        assert rc == 1

    def test_install_dev_uses_local_spec(self, dsh_home, runner, pnpm_stub, uv_stub, monkeypatch):
        _set_creds(monkeypatch)
        make_profile(dsh_home)

        assert cli.main(["install", "dsh", "--dev", "--yes"]) == 0
        assert "pnpm add " + dsh_source() in runner.commands()

    def test_uninstall_degraded_scan_lists_leftovers(
        self, dsh_home, runner, pnpm_stub, uv_stub, monkeypatch, capsys
    ):
        _set_creds(monkeypatch)
        make_profile(dsh_home)
        cli.main(["install", "dsh", "--yes"])

        # Manifest lost: uninstall must point at the leftover patch entry.
        manifest = Path(os.path.join(os.environ["HOME"], ".agentarts-memory", "installed.json"))
        manifest.unlink()
        rc = cli.main(["uninstall", "dsh", "--profile", "web", "--yes"])

        assert rc == 1
        out = capsys.readouterr().out
        assert "Found leftover entry" in out
        assert "uninstall dsh --profile web" in out

    def test_parser_flags(self):
        args = cli.build_parser().parse_args(
            ["install", "dsh", "--profile", "x", "--dsh-home", "/tmp/h", "--dev"]
        )
        assert args.profile == "x"
        assert args.dsh_home == "/tmp/h"
        assert args.dev is True
        args = cli.build_parser().parse_args(["uninstall", "dsh", "--profile", "x"])
        assert args.profile == "x"
        assert args.dsh_home is None
        assert not hasattr(args, "dev")

    def test_missing_envs_do_not_block_install(
        self, dsh_home, runner, pnpm_stub, uv_stub, monkeypatch, capsys
    ):
        # No credentials at all: install still succeeds (overlay reads env at
        # DSH launch); the summary must flag the missing actor id.
        for var in (ENV_SPACE_ID, ENV_API_KEY, ENV_ACTOR_ID):
            monkeypatch.delenv(var, raising=False)
        make_profile(dsh_home)

        assert cli.main(["install", "dsh", "--yes"]) == 0
        out = capsys.readouterr().out
        assert ENV_ACTOR_ID in out
        assert "MISSING" in out
