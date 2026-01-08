# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\Programs\\Sports Betting\\TelegramScraper\\v0.0.15\\templates', 'templates'), ('D:\\Programs\\Sports Betting\\TelegramScraper\\v0.0.15\\static', 'static'), ('D:\\Programs\\Sports Betting\\TelegramScraper\\v0.0.15\\tessdata', 'tessdata'), ('D:\\Programs\\Sports Betting\\TelegramScraper\\v0.0.15\\.env', '.'), ('D:\\Programs\\Sports Betting\\TelegramScraper\\v0.0.15\\bin\\win', 'bin/win')],
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
    a.binaries,
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
    icon=['D:\\Programs\\Sports Betting\\TelegramScraper\\v0.0.15\\static\\logo.ico'],
)
