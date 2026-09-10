# agentarts CLI - Windows one-line installer (PowerShell).
#
# Usage:
#   irm https://raw.githubusercontent.com/huaweicloud/agentarts-sdk-python/main/install.ps1 | iex
# Or, if execution policy restricts the pipe form:
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/huaweicloud/agentarts-sdk-python/main/install.ps1 | iex"
#
# Downloads the standalone agentarts binary (no Python required) from the
# latest GitHub Release, installs it to $env:LOCALAPPDATA\Programs\agentarts
# by default, and adds that directory to the user PATH.
#
# Environment overrides (useful for mirrors / custom locations):
#   $env:AGENTARTS_BIN_DIR        install directory (default: $env:LOCALAPPDATA\Programs\agentarts)
#   $env:AGENTARTS_DOWNLOAD_URL   override the download source (default: latest release asset)

$ErrorActionPreference = "Stop"

$repo = "huaweicloud/agentarts-sdk-python"
$asset = "agentarts-windows-x86_64.zip"

$installDir = if ($env:AGENTARTS_BIN_DIR) { $env:AGENTARTS_BIN_DIR } else { Join-Path $env:LOCALAPPDATA "Programs\agentarts" }
$url = if ($env:AGENTARTS_DOWNLOAD_URL) { $env:AGENTARTS_DOWNLOAD_URL } else { "https://github.com/$repo/releases/latest/download/$asset" }

Write-Host "Downloading $url ..."
$tempBase = Join-Path ([System.IO.Path]::GetTempPath()) ("agentarts-install-" + [guid]::NewGuid().ToString())
$tempDir = New-Item -ItemType Directory -Path $tempBase -Force
$zipPath = Join-Path $tempDir.FullName "agentarts.zip"

try {
    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
} catch {
    # Note: use throw (not exit) so 'irm | iex' reports the error without
    # closing the user's terminal.
    throw "Download failed. The asset '$asset' may not exist in the latest release. Check: https://github.com/$repo/releases/latest`nError: $_"
}

# Extract
Expand-Archive -Path $zipPath -DestinationPath $tempDir.FullName -Force
$extractedExe = Join-Path $tempDir.FullName "agentarts.exe"
if (-not (Test-Path $extractedExe)) {
    throw "Archive did not contain agentarts.exe."
}

# Install
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
$targetExe = Join-Path $installDir "agentarts.exe"
Copy-Item $extractedExe $targetExe -Force

# Add to user PATH (persistent) if not already present.
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -and ($userPath.Split(";") -contains $installDir)) {
    Write-Host "$installDir is already on your user PATH."
} else {
    $newPath = if ($userPath) { "$userPath;$installDir" } else { $installDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added $installDir to your user PATH."
    Write-Host "Open a NEW terminal for the PATH change to take effect."
}

# Show version (best-effort; do not fail the install if the binary errors).
try {
    & $targetExe --version
} catch {
    Write-Warning "Installed binary at $targetExe but could not run --version: $_"
}

Write-Host ""
Write-Host "Installed agentarts to $targetExe"
Write-Host "Run 'agentarts --help' (in a new terminal) to get started."

# Java agents need a local JDK 17 + Maven; the binary cannot bundle a JVM.
$javaHome = $env:JAVA_HOME
$hasMvn = $null -ne (Get-Command mvn -ErrorAction SilentlyContinue)
if ($javaHome -and $hasMvn) {
    Write-Host "(JAVA_HOME + Maven detected - Java agent dev/deploy ready.)"
} else {
    Write-Host "(For Java agents: install JDK 17 and Maven separately.)"
}
