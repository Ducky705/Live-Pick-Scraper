#!/usr/bin/env python3
"""
package_mac.py - Build and package macOS app with proper permissions

This script:
1. Runs PyInstaller to build the .app bundle
2. Sets correct executable permissions
3. Creates a distributable ZIP using ditto (preserves Unix permissions)
"""

import os
import sys
import subprocess
import shutil

# --- CONFIGURATION ---
APP_NAME = "TelegramScraper"
VERSION = "3.1.0"

def get_project_root():
    """Get the project root directory (parent of scripts/)"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_command(cmd, cwd=None):
    """Run a shell command and exit on failure"""
    print(f"  → {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        sys.exit(1)

def build():
    project_root = get_project_root()
    os.chdir(project_root)
    
    dist_dir = os.path.join(project_root, "dist")
    app_path = os.path.join(dist_dir, f"{APP_NAME}.app")
    executable_path = os.path.join(app_path, "Contents", "MacOS", APP_NAME)
    zip_path = os.path.join(dist_dir, f"{APP_NAME}-v{VERSION}.zip")
    
    # Step 1: Clean previous build
    print("\n🧹 Cleaning previous build...")
    if os.path.exists(app_path):
        shutil.rmtree(app_path)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    # Step 2: Run PyInstaller
    print("\n🔨 Building app with PyInstaller...")
    spec_file = os.path.join(project_root, "build_specs", "MacBuild.spec")
    run_command(["python", "-m", "PyInstaller", spec_file, "--noconfirm"], cwd=project_root)
    
    # Step 3: Verify build succeeded
    if not os.path.exists(executable_path):
        print(f"❌ Build failed - executable not found at {executable_path}")
        sys.exit(1)
    
    # Step 4: Set executable permissions (CRITICAL FIX)
    print("\n🔐 Setting executable permissions...")
    run_command(["chmod", "+x", executable_path])
    
    # Also set permissions on any binaries in Resources
    resources_path = os.path.join(app_path, "Contents", "Resources")
    if os.path.exists(resources_path):
        for root, dirs, files in os.walk(resources_path):
            for file in files:
                filepath = os.path.join(root, file)
                # Check if file is a Mach-O binary
                result = subprocess.run(["file", filepath], capture_output=True, text=True)
                if "Mach-O" in result.stdout or "executable" in result.stdout:
                    run_command(["chmod", "+x", filepath])
    
    # Step 5: Create distributable ZIP with ditto (preserves permissions)
    print("\n📦 Creating distributable ZIP...")
    run_command([
        "ditto", "-c", "-k", 
        "--sequesterRsrc",  # Preserve resource forks
        "--keepParent",     # Keep TelegramScraper.app folder structure
        app_path, 
        zip_path
    ])
    
    # Step 6: Verify ZIP
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n✅ Build complete!")
    print(f"   📱 App: {app_path}")
    print(f"   📦 ZIP: {zip_path} ({zip_size_mb:.1f} MB)")
    print(f"\n🚀 Ready for distribution!")

if __name__ == "__main__":
    if sys.platform != "darwin":
        print("❌ This script is for macOS only")
        sys.exit(1)
    build()
