# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone agentarts CLI binary.

Bundles the agentarts CLI plus the Huawei Cloud SDK (which uses dynamic
plugin imports that PyInstaller's static analysis misses) into a single
onefile executable that runs without a Python interpreter installed.

Verified against: the CLI's 9 top-level commands all import cleanly under
the bundle (init/config/dev/launch/invoke/runtime/destroy/gateway/memory).

Build (from repo root)::

    pyinstaller packaging/agentarts.spec --noconfirm

The Huawei Cloud SDK loads service plugins dynamically, so ``--collect-all``
is mandatory for the huaweicloudsdk* packages; ``six`` is a transitive dep
the static analyzer also misses. uvicorn/starlette load protocol/loop
backends via entry points, so they are collected too.
"""

import os

from PyInstaller.utils.hooks import collect_all

# SPECPATH is the directory containing this .spec file (provided by
# PyInstaller in the spec namespace; __file__ is not defined there).
ENTRY = os.path.join(SPECPATH, "agentarts_entry.py")

# Packages whose data files / submodules PyInstaller's static analysis
# misses. agentarts is collected so the .j2 template files are bundled.
COLLECT_PACKAGES = [
    "agentarts",
    "huaweicloudsdkcore",
    "huaweicloudsdkagentidentity",
    "huaweicloudsdkiam",
    "huaweicloudsdkswr",
    "uvicorn",
    "starlette",
]

datas = []
binaries = []
hiddenimports = ["six"]

for _pkg in COLLECT_PACKAGES:
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

a = Analysis(
    [ENTRY],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],  # minimal set — do not exclude anything the CLI imports
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="agentarts",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
