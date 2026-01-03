# auto_updater.py
"""
Auto-update module for CapperSuite.
Checks GitHub Releases for new versions and handles self-updating.
"""
import os
import sys
import json
import logging
import tempfile
import subprocess
import shutil
import zipfile
import platform
import requests
from packaging import version

# Import version and repo from config (these are static)
from config import APP_VERSION, GITHUB_REPO

# Use config values
CURRENT_VERSION = APP_VERSION

def get_github_token():
    """Get GitHub token from environment (dotenv must be loaded first)."""
    # Read dynamically from os.environ, not from config import
    # This ensures dotenv has loaded by the time this is called
    return os.environ.get('GITHUB_TOKEN', '')

def check_for_updates(github_token=None):
    """
    Check GitHub Releases API for a newer version.
    
    Returns:
        dict: {
            'update_available': bool,
            'current_version': str,
            'latest_version': str,
            'download_url': str or None,
            'release_notes': str or None,
            'error': str or None
        }
    """
    token = github_token or get_github_token()
    
    if not token:
        return {
            'update_available': False,
            'error': 'No GitHub token configured'
        }
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 404:
            return {
                'update_available': False,
                'current_version': CURRENT_VERSION,
                'latest_version': CURRENT_VERSION,
                'error': 'No releases found'
            }
        
        resp.raise_for_status()
        release = resp.json()
        
        latest_tag = release.get('tag_name', '').lstrip('v')
        release_notes = release.get('body', '')
        
        # Compare versions
        try:
            update_available = version.parse(latest_tag) > version.parse(CURRENT_VERSION)
        except:
            # Simple string comparison fallback
            update_available = latest_tag != CURRENT_VERSION
        
        # Find appropriate download asset for this platform
        download_url = None
        asset_id = None
        assets = release.get('assets', [])
        
        system = platform.system().lower()
        
        for asset in assets:
            name = asset.get('name', '').lower()
            # Match Windows or Mac based on current platform
            # Note: GitHub assets may not have .exe extension visible
            if system == 'windows':
                # Skip Mac assets
                if '.app' in name or '.dmg' in name or '.zip' in name:
                    continue
                # Match Windows patterns
                if 'windows' in name or '.exe' in name or 'win' in name or 'telegramscr' in name or 'cappersuite' in name:
                    # For private repos, use API endpoint with asset ID
                    asset_id = asset.get('id')
                    download_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/assets/{asset_id}"
                    break
            elif system == 'darwin':
                if 'mac' in name or 'darwin' in name or '.app' in name or '.dmg' in name or '.zip' in name:
                    asset_id = asset.get('id')
                    download_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/assets/{asset_id}"
                    break
        
        return {
            'update_available': update_available,
            'current_version': CURRENT_VERSION,
            'latest_version': latest_tag,
            'download_url': download_url,
            'asset_id': asset_id,
            'release_notes': release_notes,
            'error': None
        }
        
    except requests.exceptions.Timeout:
        return {
            'update_available': False,
            'error': 'Update check timed out'
        }
    except requests.exceptions.RequestException as e:
        return {
            'update_available': False,
            'error': f'Network error: {str(e)}'
        }
    except Exception as e:
        logging.error(f"Update check failed: {e}")
        return {
            'update_available': False,
            'error': str(e)
        }


def download_update(download_url, github_token=None, progress_callback=None):
    """
    Download the update file from GitHub.
    
    Args:
        download_url: URL to download from (API endpoint for private repos)
        github_token: Optional token for private repos
        progress_callback: Optional function(percent, status) for progress updates
    
    Returns:
        str: Path to downloaded file, or None on failure
    """
    token = github_token or get_github_token()
    
    headers = {
        'Accept': 'application/octet-stream'
    }
    if token:
        headers['Authorization'] = f'token {token}'
    
    try:
        if progress_callback:
            progress_callback(0, "Starting download...")
        
        resp = requests.get(download_url, headers=headers, stream=True, timeout=300)
        resp.raise_for_status()
        
        # Get filename from Content-Disposition header or derive from platform
        content_disp = resp.headers.get('Content-Disposition', '')
        if 'filename=' in content_disp:
            filename = content_disp.split('filename=')[-1].strip('"\'')
        else:
            # For API URLs, derive filename based on platform
            system = platform.system().lower()
            if system == 'windows':
                filename = 'update.exe'
            elif system == 'darwin':
                filename = 'update.zip'
            else:
                filename = 'update'
        
        # Save to temp directory
        temp_dir = tempfile.mkdtemp(prefix='cappersuite_update_')
        file_path = os.path.join(temp_dir, filename)
        
        total_size = int(resp.headers.get('content-length', 0))
        downloaded = 0
        
        with open(file_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size and progress_callback:
                        percent = int((downloaded / total_size) * 100)
                        progress_callback(percent, f"Downloading... {percent}%")
        
        if progress_callback:
            progress_callback(100, "Download complete")
        
        return file_path
        
    except Exception as e:
        logging.error(f"Download failed: {e}")
        return None


def apply_update(update_file_path, restart=True):
    """
    Apply the downloaded update.
    
    For Windows: Replace exe and restart
    For Mac: Replace .app bundle and restart
    
    Args:
        update_file_path: Path to the downloaded update file
        restart: Whether to restart the app after update
    
    Returns:
        bool: True if update was applied successfully
    """
    if not os.path.exists(update_file_path):
        logging.error(f"Update file not found: {update_file_path}")
        return False
    
    try:
        system = platform.system()
        
        if system == 'Windows':
            return _apply_windows_update(update_file_path, restart)
        elif system == 'Darwin':
            return _apply_mac_update(update_file_path, restart)
        else:
            logging.error(f"Unsupported platform: {system}")
            return False
            
    except Exception as e:
        logging.error(f"Update application failed: {e}")
        return False


def _apply_windows_update(update_file_path, restart=True):
    """Apply update on Windows."""
    if getattr(sys, 'frozen', False):
        current_exe = sys.executable
        exe_dir = os.path.dirname(current_exe)
    else:
        logging.warning("Not running as frozen app, skipping update")
        return False
    
    # Create update batch script
    batch_script = os.path.join(tempfile.gettempdir(), 'cappersuite_update.bat')
    
    # Determine if update is .exe or .zip
    if update_file_path.lower().endswith('.exe'):
        new_exe = update_file_path
    elif update_file_path.lower().endswith('.zip'):
        # Extract zip
        extract_dir = os.path.join(os.path.dirname(update_file_path), 'extracted')
        with zipfile.ZipFile(update_file_path, 'r') as z:
            z.extractall(extract_dir)
        # Find the .exe in the extracted files
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                if f.lower().endswith('.exe'):
                    new_exe = os.path.join(root, f)
                    break
            else:
                continue
            break
        else:
            logging.error("No .exe found in update package")
            return False
    else:
        new_exe = update_file_path
    
    # Write batch script that:
    # 1. Kills the running process
    # 2. Waits and retries the copy
    # 3. Starts the new exe
    # 4. Deletes itself
    exe_name = os.path.basename(current_exe)
    batch_content = f'''@echo off
taskkill /F /IM "{exe_name}" >nul 2>&1
timeout /t 3 /nobreak >nul

set RETRY=0
:RETRY_COPY
copy /Y "{new_exe}" "{current_exe}" >nul 2>&1
if errorlevel 1 (
    set /a RETRY+=1
    if %RETRY% LSS 5 (
        timeout /t 2 /nobreak >nul
        goto RETRY_COPY
    )
    exit /b 1
)
'''
    
    if restart:
        batch_content += f'''
start "" "{current_exe}"
'''
    
    batch_content += '''
del "%~f0"
'''
    
    with open(batch_script, 'w') as f:
        f.write(batch_content)
    
    # Run the batch script HIDDEN (no console window)
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0  # SW_HIDE
    
    subprocess.Popen(
        ['cmd', '/c', batch_script],
        startupinfo=startupinfo,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    # Exit current app
    if restart:
        sys.exit(0)
    
    return True


def _apply_mac_update(update_file_path, restart=True):
    """Apply update on macOS."""
    if getattr(sys, 'frozen', False):
        # Find the .app bundle path
        # sys.executable points inside the bundle
        current_app = sys.executable
        # Navigate up to find the .app
        while current_app and not current_app.endswith('.app'):
            parent = os.path.dirname(current_app)
            if parent == current_app:
                break
            current_app = parent
    else:
        logging.warning("Not running as frozen app, skipping update")
        return False
    
    if not current_app or not current_app.endswith('.app'):
        logging.error("Could not find current .app bundle")
        return False
    
    # Create update shell script
    script_path = os.path.join(tempfile.gettempdir(), 'cappersuite_update.sh')
    
    # Determine if update is .app, .zip, or .dmg
    if update_file_path.lower().endswith('.zip'):
        # Extract and find .app
        extract_dir = os.path.join(os.path.dirname(update_file_path), 'extracted')
        with zipfile.ZipFile(update_file_path, 'r') as z:
            z.extractall(extract_dir)
        # Find the .app
        for item in os.listdir(extract_dir):
            if item.endswith('.app'):
                new_app = os.path.join(extract_dir, item)
                break
        else:
            logging.error("No .app found in update package")
            return False
    elif update_file_path.lower().endswith('.app'):
        new_app = update_file_path
    else:
        logging.error(f"Unsupported update format: {update_file_path}")
        return False
    
    # Write shell script (silent, no output)
    script_content = f'''#!/bin/bash
sleep 3
rm -rf "{current_app}" 2>/dev/null

# Retry copy up to 5 times
for i in 1 2 3 4 5; do
    cp -R "{new_app}" "{os.path.dirname(current_app)}/" 2>/dev/null && break
    sleep 2
done
'''
    
    if restart:
        script_content += f'''
open "{current_app}"
'''
    
    script_content += '''
rm "$0"
'''
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    os.chmod(script_path, 0o755)
    
    # Run the script silently (detached, no terminal)
    subprocess.Popen(
        ['/bin/bash', script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    
    if restart:
        sys.exit(0)
    
    return True


def get_all_releases(github_token=None, limit=10):
    """
    Get list of all releases for the changelog/history.
    
    Returns:
        list: List of release dicts with version, date, notes
    """
    token = github_token or get_github_token()
    
    headers = {
        'Accept': 'application/vnd.github.v3+json'
    }
    if token:
        headers['Authorization'] = f'token {token}'
    
    url = f'https://api.github.com/repos/{GITHUB_REPO}/releases?per_page={limit}'
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        releases = []
        for r in resp.json():
            releases.append({
                'version': r.get('tag_name', '').lstrip('v'),
                'date': r.get('published_at', ''),
                'notes': r.get('body', ''),
                'prerelease': r.get('prerelease', False)
            })
        
        return releases
        
    except Exception as e:
        logging.error(f"Failed to fetch releases: {e}")
        return []
