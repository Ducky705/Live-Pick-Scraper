import os
import json

def generate_map():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sources = [
        os.path.join(base_dir, "tests", "samples"),
        os.path.join(base_dir, "static", "temp_images"),
    ]
    
    images = []
    MAX_IMAGES = 30
    seen_files = set()
    
    for source in sources:
        if os.path.exists(source):
            for f in os.listdir(source):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(source, f)
                    if f in seen_files:
                        continue
                    seen_files.add(f)
                    images.append(full_path.replace(os.sep, "/"))
                    
                    if len(images) >= MAX_IMAGES:
                        break
        if len(images) >= MAX_IMAGES:
            break
            
    mapping = {f"image_{i+1:02d}.jpg": path for i, path in enumerate(images)}
    
    with open(os.path.join(base_dir, "benchmark", "dataset", "image_map.json"), "w") as f:
        json.dump(mapping, f, indent=2)
        
    print(f"Generated map for {len(mapping)} images.")

if __name__ == "__main__":
    generate_map()
