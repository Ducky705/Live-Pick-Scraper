# Manual OCR Benchmark Instructions

To benchmark a manual or online AI OCR solution (like ChatGPT, Claude Pro, or Gemini Advanced) against the local engines, follow these steps:

## 1. Get the Image Dataset
The full benchmark dataset has been compiled into a single PDF:
`d:\Programs\Sports Betting\TelegramScraper\v0.0.15\benchmark\dataset\full_dataset.pdf`

## 2. Process with AI
1.  Upload this PDF to your AI of choice (e.g., ChatGPT 4o, Claude 3.5 Sonnet).
2.  Use the following **exact prompt**:

```text
I am benchmarking OCR accuracy. attached is a PDF of 30 sports betting slips.

For EACH detailed image in the PDF (there should be 30):
1. Identify the image filename/number if possible, or just index them 1-30 sequentially.
2. Transcribe the text EXACTLY as it appears.
   - Do NOT correct spelling.
   - Do NOT fix formatting.
   - Do NOT remove watermarks (like @cappersfree) - I need to test if you catch them.
3. Return the result as a SINGLE JSON object map:

{
  "image_01.jpg": "Extracted text...",
  "image_02.jpg": "Extracted text..."
}

Note: The filenames correspond to the images in order. 
If you cannot identify filenames, use keys "1", "2", "3", etc.
```

## 3. Save Results
1.  Copy the JSON output from the AI.
2.  Create a new file: `d:\Programs\Sports Betting\TelegramScraper\v0.0.15\benchmark\reports\ocr_results_manual.json`
3.  Paste the JSON content into it. It should look like this:
    ```json
    {
      "1": "extracted text...",
      "2": "extracted text..."
    }
    ```
    *(Note: If the AI uses "1", "2" keys, the benchmarking tool will automatically map them to the correct image files alphabetically).*

## 4. Run Visualization
Run the visualization tool to see how your manual entry compares:
```bash
python benchmark/tools/visualize_results.py
```
The new result will appear in the "OCR Accuracy" chart as "Manual/Online AI".
