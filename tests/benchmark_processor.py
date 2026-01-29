import logging
import time
from unittest.mock import patch

from src.parallel_batch_processor import parallel_processor

# Configure logging to suppress noise during benchmark
logging.getLogger("src.parallel_batch_processor").setLevel(logging.ERROR)


def mock_provider_response(*args, **kwargs):
    """Simulate API latency based on provider."""
    # This function isn't easily accessible inside the patch unless side_effect logic uses it
    return "Mock Response"


def run_benchmark():
    print("Generating 50 mock batches (40 simple, 5 complex, 5 images)...")
    batches = []

    # 40 Simple batches (Tier 1 candidates)
    for i in range(40):
        batches.append([{"id": i, "text": "Simple bet on Lakers -5"}])

    # 5 Complex batches (Tier 2 candidates - long text)
    for i in range(40, 45):
        batches.append([{"id": i, "text": "Complex analysis " * 500}])

    # 5 Image batches (Tier 2 candidates - vision)
    for i in range(45, 50):
        batches.append([{"id": i, "text": "Image bet", "image": "slip.jpg"}])

    print(f"Starting benchmark with {len(batches)} batches...")

    # We use side_effects to count calls and simulate delay
    call_counts = {
        "gemini": 0,
        "cerebras": 0,  # Tier 1
        "groq": 0,
        "mistral": 0,  # Tier 2
        "openrouter": 0,  # Tier 3
    }

    def gemini_side_effect(*args, **kwargs):
        time.sleep(0.05)  # Fast
        call_counts["gemini"] += 1
        return "Gemini Result"

    def cerebras_side_effect(*args, **kwargs):
        time.sleep(0.02)  # Instant
        call_counts["cerebras"] += 1
        return "Cerebras Result"

    def groq_text_side_effect(*args, **kwargs):
        time.sleep(0.2)  # Slower
        call_counts["groq"] += 1
        return "Groq Result"

    def groq_vision_side_effect(*args, **kwargs):
        time.sleep(0.5)  # Vision slow
        call_counts["groq"] += 1
        return "Groq Vision Result"

    def mistral_side_effect(*args, **kwargs):
        time.sleep(0.3)
        call_counts["mistral"] += 1
        return "Mistral Result"

    def openrouter_side_effect(*args, **kwargs):
        time.sleep(1.0)  # Slowest
        call_counts["openrouter"] += 1
        return "OpenRouter Result"

    # Patch ALL client functions
    with (
        patch(
            "src.parallel_batch_processor.gemini_text_completion",
            side_effect=gemini_side_effect,
        ),
        patch(
            "src.parallel_batch_processor.gemini_vision_completion",
            side_effect=gemini_side_effect,
        ),
        patch(
            "src.parallel_batch_processor.cerebras_completion",
            side_effect=cerebras_side_effect,
        ),
        patch(
            "src.parallel_batch_processor.groq_text_completion",
            side_effect=groq_text_side_effect,
        ),
        patch(
            "src.parallel_batch_processor.groq_vision_completion",
            side_effect=groq_vision_side_effect,
        ),
        patch(
            "src.parallel_batch_processor.mistral_completion",
            side_effect=mistral_side_effect,
        ),
        patch(
            "src.parallel_batch_processor.openrouter_completion",
            side_effect=openrouter_side_effect,
        ),
    ):
        start_time = time.time()

        # Determine which method to call
        if hasattr(parallel_processor, "process_batches_groq_priority"):
            # Old Method (simulating user choice or default)
            # But usually users called process_batches.
            # In old code, process_batches was Round Robin.
            results = parallel_processor.process_batches(batches)
        else:
            # New Method (Smart Cascading)
            results = parallel_processor.process_batches(batches)

        duration = time.time() - start_time

    print(f"\nBenchmark Complete in {duration:.2f}s")
    print("-" * 40)
    print(f"Total Batches: {len(results)}")
    print("Provider Usage:")
    for p, count in call_counts.items():
        if count > 0:
            print(f"  {p.capitalize()}: {count}")

    # Calculate synthetic 'cost' (Tier 1 = $1, Tier 2 = $10, Tier 3 = $5)
    cost = (
        (call_counts["gemini"] + call_counts["cerebras"]) * 1
        + (call_counts["groq"] + call_counts["mistral"]) * 10
        + (call_counts["openrouter"]) * 5
    )

    print(f"Estimated Synthetic Cost: ${cost}")
    print("-" * 40)


if __name__ == "__main__":
    run_benchmark()
