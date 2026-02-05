import os

from PIL import Image


def generate_pdf():
    # Define source directories
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sources = [
        os.path.join(base_dir, "benchmark", "dataset", "images"),
        os.path.join(base_dir, "static", "temp_images"),
    ]

    output_dir = os.path.join(base_dir, "benchmark", "dataset")
    os.makedirs(output_dir, exist_ok=True)
    output_pdf = os.path.join(output_dir, "full_dataset.pdf")

    images = []
    MAX_IMAGES = 30

    print(f"Searching for images (Limit: {MAX_IMAGES})...")
    seen_files = set()

    for source in sources:
        if os.path.exists(source):
            for f in os.listdir(source):
                if f.lower().endswith((".png", ".jpg", ".jpeg")):
                    full_path = os.path.join(source, f)
                    # Deduplicate by filename
                    if f in seen_files:
                        continue
                    seen_files.add(f)

                    try:
                        img = Image.open(full_path)
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        images.append(img)
                        print(f"Added: {f}")

                        if len(images) >= MAX_IMAGES:
                            break
                    except Exception as e:
                        print(f"Failed to load {f}: {e}")
            if len(images) >= MAX_IMAGES:
                break

    if not images:
        print("No images found!")
        return

    print(f"\nGenering PDF with {len(images)} images...")

    # Save as PDF
    # First image is the "base", others are appended
    main_image = images[0]
    other_images = images[1:]

    main_image.save(output_pdf, save_all=True, append_images=other_images)

    print(f"PDF Generated successfully at:\n{output_pdf}")
    print(f"Total Images: {len(images)}")


if __name__ == "__main__":
    generate_pdf()
