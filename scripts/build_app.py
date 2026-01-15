# build_app.py
import PyInstaller.__main__
import os
import sys
import shutil

# --- CONFIGURATION ---
APP_NAME = "TelegramScraper"
ENTRY_POINT = "main.py"

def get_separator():
    return ';' if sys.platform == 'win32' else ':'

def build():
    # Ensure we're in the project root (parent of scripts/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    print(f"Building from: {os.getcwd()}")
    
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
        '--onefile',
        
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
    templates_path = os.path.join(project_root, 'templates')
    static_path = os.path.join(project_root, 'static')
    args.append(f'--add-data={templates_path}{sep}templates')
    args.append(f'--add-data={static_path}{sep}static')
    
    # 2. Tesseract Data
    tessdata_path = os.path.join(project_root, 'tessdata')
    if os.path.exists('tessdata'):
        args.append(f'--add-data={tessdata_path}{sep}tessdata')

    # 3. Environment Variables (.env) - CRITICAL for API keys
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        args.append(f'--add-data={env_path}{sep}.')
        print("[OK] Bundling .env file for API keys")
    else:
        print("[WARN] .env file not found - API keys will not work in built app!")

    # 3. OS Specific Binaries & Icons
    bin_win_path = os.path.join(project_root, 'bin', 'win')
    bin_mac_path = os.path.join(project_root, 'bin', 'mac')
    
    if sys.platform == 'win32':
        args.append('--windowed')
        args.append(f'--add-data={bin_win_path}{sep}bin/win')
        if os.path.exists(os.path.join(project_root, 'static', 'logo.ico')):
            icon_path = os.path.join(project_root, 'static', 'logo.ico')
            args.append(f'--icon={icon_path}')
            
    elif sys.platform == 'darwin':
        args.append('--windowed')
        args.append(f'--add-data={bin_mac_path}{sep}bin/mac')
        args.append('--osx-bundle-identifier=com.cappersuite.app')
        
        if os.path.exists(os.path.join(project_root, 'static', 'logo.icns')):
            icon_path = os.path.join(project_root, 'static', 'logo.icns')
            args.append(f'--icon={icon_path}')
    
    print(f"Building for {sys.platform}...")
    
    # Store spec files in build_specs folder to keep root clean
    args.append('--specpath=build_specs')
    
    PyInstaller.__main__.run(args)
    print("Build Complete. Check /dist folder.")

if __name__ == "__main__":
    build()