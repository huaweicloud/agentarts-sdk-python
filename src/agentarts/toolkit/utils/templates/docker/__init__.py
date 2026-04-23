"""Docker templates for AgentArts"""

from pathlib import Path
from typing import Optional

TEMPLATES_DIR = Path(__file__).parent


def get_dockerfile_template() -> str:
    """Get the Dockerfile template content."""
    template_path = TEMPLATES_DIR / "Dockerfile.j2"
    return template_path.read_text(encoding="utf-8")


def render_dockerfile(
    base_image: str = "python:3.10-slim",
    dependency_file: str | None = None,
    entrypoint: str | None = None,
    port: int = 8080,
    user_name: str = "appuser",
    user_id: int = 1000,
    group_id: int = 1000,
    region: str | None = None,
) -> str:
    """
    Render Dockerfile from template.

    Args:
        base_image: Base Docker image
        dependency_file: Path to dependency file (e.g., requirements.txt)
        entrypoint: Entrypoint in format "module:function" (e.g., "app:main")
        port: Port to expose
        user_name: Non-root user name (default: appuser)
        user_id: Non-root user ID (default: 1000)
        group_id: Non-root group ID (default: 1000)
        region: Huawei Cloud region (e.g., "cn-southwest-2")

    Returns:
        Rendered Dockerfile content
    """
    template = get_dockerfile_template()

    if region:
        env_section = f"# Set Huawei Cloud region\nENV HUAWEICLOUD_SDK_REGION={region}"
    else:
        env_section = "# No region specified"

    user_section = f"""# Create non-root user for security
RUN groupadd -g {group_id} {user_name} && \\
    useradd -u {user_id} -g {group_id} -m -s /bin/bash {user_name}

# Install iproute2 for network interface IP detection
# Supports: Ubuntu (new/old), Debian, with multiple mirror fallbacks for China network
RUN set -e; \\
    MIRRORS="mirrors.aliyun.com mirrors.tuna.tsinghua.edu.cn mirrors.ustc.edu.cn"; \\
    \\
    switch_to_mirror() {{ \\
        mirror="$1"; \\
        if ls /etc/apt/sources.list.d/*.sources 2>/dev/null 1>&2; then \\
            for f in /etc/apt/sources.list.d/*.sources; do \\
                sed -i "s@URIs: http[s]*://[^ ]*ubuntu@URIs: http://${{mirror}}@g" "$f" 2>/dev/null || true; \\
                sed -i "s@URIs: http[s]*://[^ ]*debian@URIs: http://${{mirror}}@g" "$f" 2>/dev/null || true; \\
            done; \\
        fi; \\
        if [ -f /etc/apt/sources.list ]; then \\
            sed -i "s@http[s]*://[^ ]*archive.ubuntu.com@http://${{mirror}}@g" /etc/apt/sources.list 2>/dev/null || true; \\
            sed -i "s@http[s]*://[^ ]*security.ubuntu.com@http://${{mirror}}@g" /etc/apt/sources.list 2>/dev/null || true; \\
            sed -i "s@http[s]*://[^ ]*deb.debian.org@http://${{mirror}}@g" /etc/apt/sources.list 2>/dev/null || true; \\
            sed -i "s@http[s]*://[^ ]*security.debian.org@http://${{mirror}}@g" /etc/apt/sources.list 2>/dev/null || true; \\
        fi; \\
    }}; \\
    \\
    if apt-get update && apt-get install -y --no-install-recommends iproute2; then \\
        echo "iproute2 installed successfully"; \\
    else \\
        echo "Direct install failed, trying mirror sources..."; \\
        installed=false; \\
        for mirror in $MIRRORS; do \\
            echo "Trying mirror: $mirror"; \\
            switch_to_mirror "$mirror"; \\
            if apt-get update && apt-get install -y --no-install-recommends iproute2; then \\
                echo "iproute2 installed successfully via $mirror"; \\
                installed=true; \\
                break; \\
            fi; \\
        done; \\
        if [ "$installed" = false ]; then \\
            echo "Warning: iproute2 installation failed after all attempts, continuing without it"; \\
        fi; \\
    fi; \\
    rm -rf /var/lib/apt/lists/*"""

    chown_section = f"RUN chown {user_name}:{user_name} /app"

    if dependency_file:
        dependency_section = f"""COPY {dependency_file} .
RUN pip install --no-cache-dir -r {dependency_file}"""
    else:
        dependency_section = "# No dependency file specified"

    chown_app_section = f"RUN chown -R {user_name}:{user_name} /app"

    if entrypoint:
        module = entrypoint.split(":")[0] if ":" in entrypoint else entrypoint
        cmd_section = f'CMD ["python", "-m", "{module}"]'
    else:
        cmd_section = f'CMD ["python", "-m", "agent", "--host", "0.0.0.0", "--port", "{port}"]'

    content = template.format(
        base_image=base_image,
        env_section=env_section,
        user_section=user_section,
        chown_section=chown_section,
        dependency_section=dependency_section,
        chown_app_section=chown_app_section,
        port=port,
        user_name=user_name,
        cmd_section=cmd_section,
    )

    lines = content.split("\n")
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if line.strip() == "":
            if not prev_empty:
                cleaned_lines.append(line)
            prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False

    return "\n".join(cleaned_lines)
