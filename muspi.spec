# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 项目根目录
project_root = os.path.dirname(os.path.abspath(SPEC))

# 收集所有隐藏导入
hiddenimports = []
hiddenimports += collect_submodules('luma')
hiddenimports += collect_submodules('PIL')
hiddenimports += collect_submodules('evdev')
hiddenimports += collect_submodules('gpiozero')
hiddenimports += collect_submodules('lgpio')
hiddenimports += collect_submodules('pydbus')
hiddenimports += collect_submodules('roonapi')
hiddenimports += collect_submodules('opuslib')
hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('scipy')
hiddenimports += collect_submodules('paho')
hiddenimports += collect_submodules('musicbrainzngs')
hiddenimports += collect_submodules('libretro')
hiddenimports += collect_submodules('pyaudio')
hiddenimports += collect_submodules('alsaaudio')
hiddenimports += collect_submodules('pyarduboy')

# 添加其他常用模块
hiddenimports += ['requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna']
hiddenimports += ['websocket', 'websocket._abnf', 'websocket._app', 'websocket._core']

# 收集数据文件
datas = []
datas += collect_data_files('luma')

# 添加项目配置文件和资源
datas += [(os.path.join(project_root, 'config'), 'config')]
datas += [(os.path.join(project_root, 'assets'), 'assets')]

# 添加所有 Python 模块
datas += [(os.path.join(project_root, 'screen'), 'screen')]
datas += [(os.path.join(project_root, 'ui'), 'ui')]
datas += [(os.path.join(project_root, 'until'), 'until')]
datas += [(os.path.join(project_root, 'drive'), 'drive')]

# 分析
a = Analysis(
    [os.path.join(project_root, 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='muspi',
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
    name='muspi',
)
