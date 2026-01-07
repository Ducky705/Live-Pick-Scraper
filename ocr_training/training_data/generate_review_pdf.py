# training_data/generate_review_pdf.py
"""
Generate a PDF with all images and their OCR text for AI review.
"""

import sys
import os
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT


def generate_pdf():
    """Generate PDF with images and OCR text."""
    
    gt_dir = Path(__file__).parent / "ground_truth"
    samples_dir = Path(__file__).parent.parent / "tests" / "samples"
    output_path = Path(__file__).parent / "ocr_review.pdf"
    
    files = sorted(gt_dir.glob("*.gt.txt"))
    
    doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                           leftMargin=0.5*inch, rightMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=14, spaceAfter=10)
    ocr_style = ParagraphStyle('OCR', parent=styles['Normal'], fontSize=10, 
                               fontName='Courier', spaceAfter=20, leftIndent=20)
    
    story = []
    
    # Title page
    story.append(Paragraph("OCR Ground Truth Review", styles['Title']))
    story.append(Paragraph("Review each image and correct the OCR text below it.", styles['Normal']))
    story.append(Spacer(1, 20))
    
    for i, gt_file in enumerate(files, 1):
        base_name = gt_file.stem.replace(".gt", "")
        orig_image = samples_dir / f"{base_name}.jpg"
        
        if not orig_image.exists():
            continue
        
        # Image title
        story.append(Paragraph(f"Image {i}: {base_name}", title_style))
        
        # Add image
        img = Image.open(orig_image)
        img_width = 6 * inch
        aspect = img.height / img.width
        img_height = img_width * aspect
        if img_height > 4 * inch:
            img_height = 4 * inch
            img_width = img_height / aspect
        
        # Save to buffer
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        story.append(RLImage(buffer, width=img_width, height=img_height))
        story.append(Spacer(1, 10))
        
        # OCR text
        with open(gt_file, 'r', encoding='utf-8') as f:
            ocr_text = f.read()
        
        # Escape special characters for reportlab
        ocr_text = ocr_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        ocr_text = ocr_text.replace('\n', '<br/>')
        
        story.append(Paragraph("<b>Current OCR:</b>", styles['Normal']))
        story.append(Paragraph(ocr_text, ocr_style))
        story.append(PageBreak())
    
    doc.build(story)
    print(f"✅ PDF generated: {output_path}")
    return output_path


def generate_text_file():
    """Generate a simple text file with all images and OCR for AI review."""
    
    gt_dir = Path(__file__).parent / "ground_truth"
    output_path = Path(__file__).parent / "ocr_review.txt"
    
    files = sorted(gt_dir.glob("*.gt.txt"))
    
    with open(output_path, 'w', encoding='utf-8') as out:
        for i, gt_file in enumerate(files, 1):
            base_name = gt_file.stem.replace(".gt", "")
            
            with open(gt_file, 'r', encoding='utf-8') as f:
                ocr_text = f.read()
            
            out.write(f"=== IMAGE {i}: {base_name} ===\n")
            out.write(f"OCR OUTPUT:\n")
            out.write(ocr_text)
            out.write("\n\n---CORRECTED TEXT---\n")
            out.write("[AI: Write corrected text here]\n")
            out.write("\n" + "="*60 + "\n\n")
    
    print(f"✅ Text file generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_pdf()
    generate_text_file()
