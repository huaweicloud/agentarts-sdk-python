"""Tests for the Dockerfile rendered by the AgentArts CLI."""

from agentarts.toolkit.utils.templates.docker import render_dockerfile


def test_app_files_are_readable_regardless_of_host_umask():
    """`COPY . .` carries the build host's umask into the image.

    On EulerOS (umask 0027) that is 0640/0750, and chown only fixes ownership.
    The image must therefore widen the mode bits, otherwise any runtime UID
    other than appuser cannot read /app and the container never starts.
    """
    dockerfile = render_dockerfile()

    assert "chmod -R a+rX /app" in dockerfile
    assert dockerfile.index("COPY . .") < dockerfile.index("chmod -R a+rX /app")
    assert dockerfile.index("chmod -R a+rX /app") < dockerfile.index("USER appuser")
