# build_app.py
import PyInstaller.__main__
import os
import sys
import shutil

# --- CONFIGURATION ---
APP_NAME = "CapperSuite"
ENTRY_POINT = "main.py"

def get_separator():
    return ';' if sys.platform == 'win32' else ':'

def build():
    # Base arguments
    args = [
        ENTRY_POINT,
        f'--name={APP_NAME}',
        '--noconfirm',
        '--clean',
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=notebook',
        '--exclude-module=scipy',
        '--exclude-module=pandas', 
        '--exclude-module=numpy',
        
        # --- FIX: ADD THESE HIDDEN IMPORTS ---
        '--hidden-import=webview',
        '--hidden-import=webview.platforms.winforms',      # Required for Windows
        '--hidden-import=webview.platforms.edgechromium',  # Required for Edge
        '--hidden-import=clr',                             # Required for pythonnet
        '--hidden-import=System',                          # Required for .NET interaction
        # -------------------------------------
    ]

    # --- DATA BUNDLING ---
    sep = get_separator()
    
    # 1. Web Assets
    args.append(f'--add-data=templates{sep}templates')
    args.append(f'--add-data=static{sep}static')
    
    # 2. Tesseract Data
    if os.path.exists('tessdata'):
        args.append(f'--add-data=tessdata{sep}tessdata')

    # 3. OS Specific Binaries & Icons
    if sys.platform == 'win32':
        args.append('--windowed')
        args.append(f'--add-data=bin/win{sep}bin/win')
        if os.path.exists('static/logo.ico'):
            args.append('--icon=static/logo.ico')
            
    elif sys.platform == 'darwin':
        args.append('--windowed')
        args.append(f'--add-data=bin/mac{sep}bin/mac')
        args.append('--osx-bundle-identifier=com.cappersuite.app')
        
        if os.path.exists('static/logo.icns'):
            args.append('--icon=static/logo.icns')
    
    print(f"Building for {sys.platform}...")
    PyInstaller.__main__.run(args)
    print("Build Complete. Check /dist folder.")

if __name__ == "__main__":
    build()