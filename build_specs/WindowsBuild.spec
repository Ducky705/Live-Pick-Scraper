# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Windows Spec File
# Ensure 'bin/win' contains tesseract.exe and all DLLs.

a = Analysis(
    ['..\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('..\\bin\\win', 'bin\\win'),
        ('..\\tessdata', 'tessdata'),
        ('..\\static', 'static'),
        ('..\\templates', 'templates'),
        ('..\\src', 'src'),
        ('..\\.env', '.'),
    ],
    hiddenimports=[
        'waitress',
        'webview',
        'webview.platforms.winforms', 
        'webview.platforms.edgechromium',
        'clr', 
        'System',
        'PIL',
        'cv2',
        'telethon',
        'supabase',
        'dotenv',
        'packaging'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'PyQt5', 'qtpy', 'torch',
        'tensorflow', 'notebook', 'ipython', 'lxml', 'bokeh', 'dask', 'tkinter', 'numpy'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CapperSuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Windowed mode (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['..\\static\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CapperSuite',
)
