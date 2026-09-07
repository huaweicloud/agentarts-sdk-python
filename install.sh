#!/bin/sh
# agentarts CLI — one-line installer for Linux/macOS.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/huaweicloud/agentarts-sdk-python/main/install.sh | sh
#
# Downloads the appropriate standalone binary (no Python required) from the
# latest GitHub Release, installs it to $AGENTARTS_BIN_DIR (default
# ~/.local/bin, or /usr/local/bin when run with sudo), and prints next steps.
#
# Windows is not supported by this script — Windows users should download
# agentarts-windows-x86_64.exe from the Release page directly.

set -eu

REPO="huaweicloud/agentarts-sdk-python"
INSTALL_DIR="${AGENTARTS_BIN_DIR:-${HOME}/.local/bin}"

# --- detect platform ------------------------------------------------------- #
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Linux*)  os=linux ;;
  Darwin*) os=darwin ;;
  *) printf 'Unsupported OS: %s\n' "$OS" >&2; exit 1 ;;
esac

case "$ARCH" in
  x86_64|amd64)  arch=x86_64 ;;
  aarch64|arm64) arch=arm64 ;;
  *) printf 'Unsupported architecture: %s\n' "$ARCH" >&2; exit 1 ;;
esac

ASSET="agentarts-${os}-${arch}.tar.gz"

# --- pick install dir ------------------------------------------------------ #
# If running as root (sudo) and no override, use a system-wide location.
if [ "$(id -u)" -eq 0 ] && [ -z "${AGENTARTS_BIN_DIR:-}" ]; then
  INSTALL_DIR="/usr/local/bin"
fi

# --- download -------------------------------------------------------------- #
# AGENTARTS_DOWNLOAD_URL overrides the source (e.g. a mirror or local file).
URL="${AGENTARTS_DOWNLOAD_URL:-https://github.com/${REPO}/releases/latest/download/${ASSET}}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

printf 'Downloading %s ...\n' "$URL"
if ! curl -fSL --retry 3 -o "${TMPDIR}/${ASSET}" "$URL"; then
  printf 'Download failed. The asset "%s" may not exist in the latest release.\n' "$ASSET" >&2
  printf 'Check available assets at: https://github.com/%s/releases/latest\n' "$REPO" >&2
  exit 1
fi

# --- extract --------------------------------------------------------------- #
tar -xzf "${TMPDIR}/${ASSET}" -C "$TMPDIR"
BIN="${TMPDIR}/agentarts"
if [ ! -f "$BIN" ]; then
  printf 'Archive did not contain an "agentarts" binary.\n' >&2
  exit 1
fi

# --- install ---------------------------------------------------------------- #
mkdir -p "$INSTALL_DIR"
mv "$BIN" "${INSTALL_DIR}/agentarts"
chmod +x "${INSTALL_DIR}/agentarts"

# --- report ----------------------------------------------------------------- #
printf '\nInstalled agentarts to %s\n' "${INSTALL_DIR}/agentarts"

if ! command -v agentarts >/dev/null 2>&1; then
  case ":$PATH:" in
    *:"${INSTALL_DIR}":*) ;;  # already on PATH
    *)
      printf '\nNOTE: "%s" is not on your PATH. Add it, e.g. in ~/.bashrc:\n' "$INSTALL_DIR"
      printf '    export PATH="%s:$PATH"\n' "$INSTALL_DIR"
      printf 'Then start a new shell or: source ~/.bashrc\n'
      ;;
  esac
fi

if command -v agentarts >/dev/null 2>&1; then
  printf '\n'
  agentarts --version || true
  printf '\nRun `agentarts --help` to get started.\n'
else
  printf '\nRun `%s/agentarts --help` to get started.\n' "$INSTALL_DIR"
fi

# Java agents need a local JDK 17 + Maven; the binary cannot bundle a JVM.
if command -v java >/dev/null 2>&1 && command -v mvn >/dev/null 2>&1; then
  printf '(JDK + Maven detected — Java agent dev/deploy ready.)\n'
else
  printf '(For Java agents: install JDK 17 and Maven separately.)\n'
fi
