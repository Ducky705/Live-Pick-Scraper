# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static'), ('tessdata', 'tessdata'), ('bin/win', 'bin/win'), ('src', 'src'), ('.env', '.')],
    hiddenimports=['webview', 'waitress', 'packaging'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'numpy', 'scipy', 'pandas', 'matplotlib', 'notebook', 'IPython', 'bokeh', 'dask', 'PyQt5', 'tkinter', 'lxml'],
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
    name='CapperSuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['static\\logo.ico'],
)
