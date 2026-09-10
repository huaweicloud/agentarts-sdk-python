"""Java dev server operation.

Runs a Java agent in a child JVM for ``agentarts dev``. Unlike the Python
dev path (which loads the ASGI app in-process via uvicorn), Java agents are
compiled with Maven and launched as a separate ``java`` process whose
``main(String[])`` binds the HTTP server (``POST /invocations``,
``GET /ping``).

The flow mirrors the former Java toolkit CLI's ``DevOperation``:

1. ``mvn compile`` + ``build-classpath`` (writes
   ``target/agentarts-dev-classpath.txt``).
2. Assemble classpath = ``target/classes`` + the file contents.
3. Write an argfile (``@argfile``) to bypass command-line length limits.
4. Spawn ``java @argfile`` with ``PORT``/``HOST`` env so the agent's
   ``main()`` binds the dev port; inject config + ``--env`` vars.
5. Poll ``GET /ping`` until ready.
6. On ``--reload``: poll source mtime every 750ms; on change, debounce
   250ms, kill the JVM tree, rebuild, restart.

Requires a local JDK 17 + Maven on ``PATH`` (the binary bundles a Python
interpreter but cannot bundle a JVM).
"""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
from rich.console import Console

from agentarts.toolkit.operations.runtime.dev import (
    format_env_display,
    get_entrypoint,
    inject_environment_variables,
    load_config,
)
from agentarts.toolkit.utils.common import echo_error, echo_info

console = Console()

# Timing budgets (mirrors the former Java DevOperation).
RELOAD_POLL_SECONDS = 0.75
RELOAD_DEBOUNCE_SECONDS = 0.25
BUILD_TIMEOUT_SECONDS = 600
READY_TIMEOUT_SECONDS = 60

CLASSPATH_FILE = Path("target") / "agentarts-dev-classpath.txt"
ARGFILE_PATH = Path("target") / "agentarts-dev-argfile"

# Files/dirs fingerprinted for hot reload.
WATCH_PATHS = [
    Path("pom.xml"),
    Path("src/main/java"),
    Path("src/main/resources"),
    Path(".agentarts_config.yaml"),
]


def run_java_dev_server(
    port: int,
    host: str,
    reload: bool,
    config_path: str | None,
    env_vars: dict[str, str] | None = None,
) -> bool:
    """Run a Java agent in a child JVM for local development."""
    config = load_config(config_path)
    entrypoint = get_entrypoint(config)
    if not entrypoint:
        echo_error("No entrypoint found in configuration")
        console.print("[dim]Please set 'base.entrypoint' (Java main class, e.g. com.example.Agent) in .agentarts_config.yaml[/dim]")
        return False

    os.environ["AGENTARTS_ENV"] = "development"
    os.environ["AGENTARTS_CONFIG"] = config_path or ".agentarts_config.yaml"
    inject_environment_variables(config, env_vars)

    env_display = format_env_display(env_vars, config)

    console.print()
    echo_info(
        "Development Server (Java)",
        f"[cyan]Host:[/cyan] [white]{host}[/white]\n[cyan]Port:[/cyan] [white]{port}[/white]\n[cyan]Config:[/cyan] [yellow]{config_path or '.agentarts_config.yaml'}[/yellow]\n[cyan]Entrypoint:[/cyan] [yellow]{entrypoint}[/yellow]\n[cyan]Auto-reload:[/cyan] [green]{'enabled' if reload else 'disabled'}[/green]{env_display}",
    )
    console.print()
    console.print(f"[cyan]Invocation Endpoint:[/cyan] [white]POST[/white] [link]http://{host}:{port}/invocations[/link]")
    console.print(f"[cyan]Health Check:[/cyan] [white]GET[/white] [link]http://{host}:{port}/ping[/link]")
    console.print()

    if not _prepare_project():
        return False

    proc = _start_child(entrypoint, port, host)
    if proc is None:
        return False

    if not _wait_ready(port):
        _terminate_tree(proc)
        return False

    if not reload:
        try:
            proc.wait()
            return True
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down dev server...[/yellow]")
            return True
        finally:
            _terminate_tree(proc)

    # Hot reload loop.
    last_fingerprint = _fingerprint()
    try:
        while True:
            time.sleep(RELOAD_POLL_SECONDS)
            current = _fingerprint()
            if current == last_fingerprint:
                continue
            # Debounce: confirm the change settled.
            time.sleep(RELOAD_DEBOUNCE_SECONDS)
            current = _fingerprint()
            if current == last_fingerprint:
                continue
            last_fingerprint = current
            console.print("\n[cyan]Source change detected — rebuilding and restarting...[/cyan]")
            _terminate_tree(proc)
            if not _prepare_project():
                console.print("[red]Rebuild failed; keeping previous build stopped. Fix errors and restart 'agentarts dev'.[/red]")
                return False
            proc = _start_child(entrypoint, port, host)
            if proc is None or not _wait_ready(port):
                if proc is not None:
                    _terminate_tree(proc)
                return False
            console.print("[green]Reloaded.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down dev server...[/yellow]")
        return True
    finally:
        _terminate_tree(proc)
        _cleanup_artifacts()


# --------------------------------------------------------------------------- #
# Build & classpath
# --------------------------------------------------------------------------- #
def _prepare_project() -> bool:
    """Compile the Maven project and build the runtime classpath file."""
    mvn = _find_mvn()
    cmd = [
        mvn,
        "-q",
        "-B",
        "-DskipTests",
        "compile",
        "org.apache.maven.plugins:maven-dependency-plugin:3.11.0:build-classpath",
        "-DincludeScope=runtime",
        "-Dmdep.outputFile=" + str(CLASSPATH_FILE),
    ]
    console.print("[dim]Building (mvn compile + build-classpath)...[/dim]")
    try:
        result = subprocess.run(
            cmd,
            timeout=BUILD_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        echo_error(f"Maven build timed out after {BUILD_TIMEOUT_SECONDS}s")
        return False
    except FileNotFoundError:
        echo_error(f"Cannot run Maven ('{mvn}' not found). Install Maven and ensure it is on PATH.")
        return False
    if result.returncode != 0:
        echo_error(f"Maven build failed (exit {result.returncode})")
        return False
    return True


def _assemble_classpath() -> str | None:
    """Assemble the runtime classpath: target/classes + dependency jars."""
    parts = [str(Path("target/classes"))]
    if CLASSPATH_FILE.exists():
        dep_cp = CLASSPATH_FILE.read_text(encoding="utf-8").strip()
        if dep_cp:
            parts.append(dep_cp)
    elif Path("target/dependency").exists():
        # Fallback: dependency:copy-dependencies output (not produced by
        # build-classpath, but kept for parity with the former Java CLI).
        parts.extend(str(p) for p in sorted(Path("target/dependency").glob("*.jar")))
    else:
        echo_error(f"Classpath file not found: {CLASSPATH_FILE}")
        console.print("[dim]Did 'mvn compile' succeed?[/dim]")
        return None
    return os.pathsep.join(parts)


# --------------------------------------------------------------------------- #
# Child JVM lifecycle
# --------------------------------------------------------------------------- #
def _start_child(entrypoint: str, port: int, host: str) -> subprocess.Popen | None:
    """Spawn the agent JVM in a new process group and return the handle."""
    classpath = _assemble_classpath()
    if classpath is None:
        return None

    java = _find_java()
    if java is None:
        echo_error("Cannot find a Java runtime. Set JAVA_HOME or put 'java' on PATH.")
        return None

    Path("target").mkdir(parents=True, exist_ok=True)
    # Quote the classpath in the argfile so paths with spaces survive.
    ARGFILE_PATH.write_text(
        f'-cp\n"{classpath}"\n{entrypoint}\n',
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PORT"] = str(port)
    env["HOST"] = host

    popen_kwargs: dict = {
        "env": env,
        "stdout": sys.stdout,
        "stderr": sys.stderr,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    try:
        return subprocess.Popen([java, "@" + str(ARGFILE_PATH)], **popen_kwargs)
    except FileNotFoundError:
        echo_error(f"Cannot launch Java runtime ('{java}' not found).")
        return None


def _terminate_tree(proc: subprocess.Popen) -> None:
    """Terminate the JVM and its whole process tree."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except ProcessLookupError:
                return
            _wait_for_exit(proc, timeout=5)
            if proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
    except Exception:
        proc.kill()


def _wait_for_exit(proc: subprocess.Popen, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.1)


def _wait_ready(port: int) -> bool:
    """Poll GET /ping until the agent is up or READY_TIMEOUT elapses."""
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    url = f"http://127.0.0.1:{port}/ping"
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=2.0).status_code == 200:
                return True
        except httpx.ConnectError:
            pass  # JVM still starting up — retry.
        time.sleep(0.3)
    echo_error(f"Agent did not become ready at {url} within {READY_TIMEOUT_SECONDS}s")
    return False


# --------------------------------------------------------------------------- #
# Hot reload fingerprint
# --------------------------------------------------------------------------- #
def _fingerprint() -> str:
    """Hash mtime+size of watched source files into a stable digest."""
    h = hashlib.sha1()  # noqa: S324 — non-crypto digest
    for path in WATCH_PATHS:
        if path.is_file():
            _fold(h, path)
        elif path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file():
                    _fold(h, f)
    return h.hexdigest()


def _fold(h, path: Path) -> None:
    try:
        st = path.stat()
    except OSError:
        return
    h.update(str(path).encode())
    h.update(str(st.st_mtime).encode())
    h.update(str(st.st_size).encode())


# --------------------------------------------------------------------------- #
# Toolchain discovery & cleanup
# --------------------------------------------------------------------------- #
def _find_mvn() -> str:
    if sys.platform == "win32":
        for cand in ("mvn.cmd", "mvn.bat"):
            if _on_path(cand):
                return cand
    return "mvn"


def _find_java() -> str | None:
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        exe = "java.exe" if sys.platform == "win32" else "java"
        candidate = Path(java_home) / "bin" / exe
        if candidate.exists():
            return str(candidate)
    # Fall back to java.home (set by a JVM) then PATH.
    java_home = os.environ.get("java.home") or os.environ.get("JDK_HOME")
    if java_home:
        exe = "java.exe" if sys.platform == "win32" else "java"
        candidate = Path(java_home) / "bin" / exe
        if candidate.exists():
            return str(candidate)
    if _on_path("java.exe" if sys.platform == "win32" else "java"):
        return "java"
    return None


def _on_path(executable: str) -> bool:
    paths = os.environ.get("PATH", "")
    for p in paths.split(os.pathsep):
        if p and (Path(p) / executable).exists():
            return True
    return False


def _cleanup_artifacts() -> None:
    """Remove dev classpath/argfile artifacts (best-effort, with retries)."""
    for artifact in (CLASSPATH_FILE, ARGFILE_PATH):
        if not artifact.exists():
            continue
        for _ in range(60):
            try:
                artifact.unlink()
                break
            except OSError:
                time.sleep(0.05)
