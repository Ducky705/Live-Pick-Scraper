import os
import sys
import logging

sys.path.insert(0, r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15')
logging.basicConfig(level=logging.INFO)

from src.openrouter_client import openrouter_completion

models_to_test = [
    'arcee-ai/trinity-large-preview:free',
    'qwen/qwen3-235b-a22b-thinking-2507'
]

with open('golden_set_prompt.txt', 'r', encoding='utf-8') as f:
    prompt = f.read()

for model in models_to_test:
    print(f'\n--- Testing model: {model} ---')
    try:
        # Some models take longer, so we use a 180s timeout
        result = openrouter_completion(prompt, model=model, timeout=180, max_cycles=1)
        filename = f"test_ai_output_{model.replace('/', '_').replace(':', '_')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(result if result else 'EMPTY RESPONSE')
        print(f'Model {model} completed. Output saved to {filename}')
    except Exception as e:
        print(f'Error testing {model}: {e}')
