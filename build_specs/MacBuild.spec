# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Resolve paths relative to project root (parent of build_specs/)
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
PROJECT_ROOT = os.path.dirname(SPEC_DIR)
os.chdir(PROJECT_ROOT)

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'bin/mac'), 'bin/mac'),
        # Only include eng.traineddata (4MB) - osd.traineddata (10MB) not needed for PSM 6
        (os.path.join(PROJECT_ROOT, 'tessdata/eng.traineddata'), 'tessdata'),
        # Selectively include static assets - exclude temp_images (49MB runtime cache)
        (os.path.join(PROJECT_ROOT, 'static/css'), 'static/css'),
        (os.path.join(PROJECT_ROOT, 'static/js'), 'static/js'),
        (os.path.join(PROJECT_ROOT, 'static/dist'), 'static/dist'),
        (os.path.join(PROJECT_ROOT, 'static/logo.icns'), 'static'),
        (os.path.join(PROJECT_ROOT, 'static/logo.ico'), 'static'),
        (os.path.join(PROJECT_ROOT, 'templates'), 'templates'),
        (os.path.join(PROJECT_ROOT, 'src'), 'src'),
        (os.path.join(PROJECT_ROOT, '.env'), '.'),
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
        # UI frameworks we don't use
        'matplotlib', 'PyQt5', 'PyQt6', 'qtpy', 'PySide2', 'PySide6',
        'tkinter', '_tkinter', 'Tkinter',
        # Heavy ML/data libs
        'torch', 'tensorflow', 'keras', 'numpy.testing',
        'scipy', 'pandas', 'sklearn', 'scikit-learn',
        # Dev tools (mypy adds 5.7MB)
        'notebook', 'jupyter', 'ipython', 'IPython',
        'mypy', 'mypyc',
        # Messaging libs not used
        'zmq', 'pyzmq',
        # Other heavy unused
        'lxml', 'bokeh', 'dask', 'numba', 'sympy',
        'pytest', 'unittest', 'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ONEDIR MODE: EXE only contains scripts, not binaries/datas
exe = EXE(
    pyz,
    a.scripts,
    [],  # Empty - binaries go in COLLECT
    exclude_binaries=True,  # KEY CHANGE: binaries collected separately
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

# COLLECT: Gathers all components into a folder (onedir mode)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TelegramScraper',
)

# BUNDLE: Wraps the collected folder into a macOS .app
app = BUNDLE(
    coll,  # Use collected folder, not exe directly
    name='TelegramScraper.app',
    icon=os.path.join(PROJECT_ROOT, 'static/logo.icns'),
    bundle_identifier='com.diegosargent.telegramscraper',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '2.0.3',
    },
)
