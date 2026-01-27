from src.extraction_pipeline import ExtractionPipeline
import json


def reproduce():
    text = "**Big Al**\n\nNHL Selections\n1* Oilers -175, 10:05 pm"
    pipeline = ExtractionPipeline()

    # We simulate a message dictionary
    message = {
        "text": text,
        "id": 12793,
        "date": "2026-01-24 12:03 ET",
        "source": "Telegram",
    }

    result = pipeline.run([message], target_date="2026-01-24")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    reproduce()
