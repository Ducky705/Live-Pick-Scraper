import os
import shutil
import subprocess
import sys
from PIL import Image # pip install Pillow

def convert_ico_to_icns():
    print("\n" + "="*50)
    print("STEP 1: CONVERTING ICO TO ICNS")
    print("="*50)
    
    ico_path = os.path.join('static', 'logo.ico')
    icns_path = os.path.join('static', 'logo.icns')
    iconset_dir = os.path.join('static', 'logo.iconset')

    # 1. Check if source exists
    if not os.path.exists(ico_path):
        print(f"Error: {ico_path} not found.")
        return False

    # 2. Clean up old files
    if os.path.exists(icns_path):
        os.remove(icns_path)
    if os.path.exists(iconset_dir):
        shutil.rmtree(iconset_dir)
    os.makedirs(iconset_dir)

    try:
        # 3. Open ICO
        img = Image.open(ico_path)
        
        # Ensure we are working with RGBA (Transparency)
        img = img.convert("RGBA")

        # 4. Generate required sizes for macOS .iconset
        # macOS requires specific filenames and resolutions
        definitions = [
            ('icon_16x16.png', 16),
            ('icon_16x16@2x.png', 32),
            ('icon_32x32.png', 32),
            ('icon_32x32@2x.png', 64),
            ('icon_128x128.png', 128),
            ('icon_128x128@2x.png', 256),
            ('icon_256x256.png', 256),
            ('icon_256x256@2x.png', 512),
            ('icon_512x512.png', 512),
            ('icon_512x512@2x.png', 1024),
        ]

        print("Generating icon sizes...")
        for filename, size in definitions:
            # High-quality resize
            resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
            resized_img.save(os.path.join(iconset_dir, filename))

        # 5. Use native Mac tool 'iconutil' to pack them
        print("Packing into .icns...")
        subprocess.run(['iconutil', '-c', 'icns', iconset_dir], check=True)
        
        print(f"Success! Created: {icns_path}")
        
        # Cleanup temp folder
        shutil.rmtree(iconset_dir)
        return True

    except Exception as e:
        print(f"Failed to convert icon: {e}")
        # Cleanup on fail
        if os.path.exists(iconset_dir):
            shutil.rmtree(iconset_dir)
        return False

def clean_dist():
    # Force clean dist folder to prevent "Directory not empty" errors
    dist_path = 'dist'
    if os.path.exists(dist_path):
        print(f"Cleaning {dist_path}...")
        try:
            shutil.rmtree(dist_path)
        except OSError:
            subprocess.run(['rm', '-rf', dist_path])

def build():
    print("\n" + "="*50)
    print("STEP 2: BUILDING APP")
    print("="*50)
    
    # Clean first
    clean_dist()
    
    # Run build script
    subprocess.run([sys.executable, 'build_app.py'])

if __name__ == "__main__":
    # 1. Convert Icon
    if convert_ico_to_icns():
        # 2. Build
        build()
    else:
        print("Skipping build due to icon error.")