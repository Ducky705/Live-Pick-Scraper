import os
from dotenv import load_dotenv

load_dotenv()

tokens = [
    "GROQ_TOKEN", 
    "OPENROUTER_API_KEY", 
    "CEREBRAS_TOKEN", 
    "MISTRAL_TOKEN", 
    "GEMINI_TOKEN"
]

print("--- Token Check ---")
for t in tokens:
    val = os.getenv(t)
    status = "FOUND" if val else "MISSING"
    print(f"{t}: {status}")
