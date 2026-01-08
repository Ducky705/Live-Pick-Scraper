# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/diegosargent/Documents/Programs/Telegram Scraper 2.0/templates', 'templates'), ('/Users/diegosargent/Documents/Programs/Telegram Scraper 2.0/static', 'static'), ('/Users/diegosargent/Documents/Programs/Telegram Scraper 2.0/tessdata', 'tessdata'), ('/Users/diegosargent/Documents/Programs/Telegram Scraper 2.0/.env', '.'), ('/Users/diegosargent/Documents/Programs/Telegram Scraper 2.0/bin/mac', 'bin/mac')],
    hiddenimports=['webview', 'webview.platforms.winforms', 'webview.platforms.edgechromium', 'clr', 'System'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'notebook', 'scipy', 'pandas', 'numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TelegramScraper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/diegosargent/Documents/Programs/Telegram Scraper 2.0/static/logo.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TelegramScraper',
)
app = BUNDLE(
    coll,
    name='TelegramScraper.app',
    icon='/Users/diegosargent/Documents/Programs/Telegram Scraper 2.0/static/logo.icns',
    bundle_identifier='com.cappersuite.app',
)
