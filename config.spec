# -*- mode: python ; coding: utf-8 -*-

import os

# 项目根目录
project_root = os.path.dirname(os.path.abspath(SPEC))

# 收集数据文件
datas = []
datas += [(os.path.join(project_root, 'config'), 'config')]
datas += [(os.path.join(project_root, 'muspi.service'), '.')]

# 分析
a = Analysis(
    [os.path.join(project_root, 'config.py')],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='muspi-config',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='muspi-config',
)
