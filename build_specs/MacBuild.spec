# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('bin/mac', 'bin/mac'),
        ('tessdata', 'tessdata'),
        ('static', 'static'),
        ('templates', 'templates'),
        ('src', 'src'),
        ('.env', '.'),
    ],
    hiddenimports=[
        'waitress',
        'webview',
        'PIL',
        'cv2',
        'telethon',
        'supabase',
        'dotenv'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'PyQt5', 'qtpy', 'torch',
        'tensorflow', 'notebook', 'ipython', 'lxml', 'bokeh', 'dask'
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TelegramScraper',
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
)

app = BUNDLE(
    exe,
    name='TelegramScraper.app',
    icon='static/logo.icns',
    bundle_identifier='com.diegosargent.telegramscraper',
    info_plist={
        'NSHighResolutionCapable': 'True'
    },
)
