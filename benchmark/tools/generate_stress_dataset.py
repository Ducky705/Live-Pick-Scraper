import json
import random


def generate_stress_dataset(
    output_path="benchmark/dataset/stress_test_500.json", count=500
):
    dataset = []

    # Simple templates (Rule-based)
    simple_templates = [
        "Lakers -5",
        "Celtics -3.5",
        "Warriors vs Suns Over 230",
        "Knicks +4",
        "Miami Heat ML",
        "Bulls -2.5 @ Pistons",
        "Nets vs Raptors Under 215.5",
    ]

    # Complex templates (AI-required)
    complex_templates = [
        "I'm loving the way the Lakers are playing lately. I think they cover the -5 spread easily against the tired Kings.",
        "Maximum bet on the over in the Warriors game. Curry is hot and the defense is non-existent. 230 is too low.",
        "Fade the public here. Everyone is on the Knicks but the smart money is on the Sixers +2.",
        "My model shows significant value on the under 215.5 for Nets/Raptors. Pace should be slow.",
        "Big play alert: Miami Heat to win outright. Jimmy Butler is back.",
    ]

    for i in range(1, count + 1):
        is_simple = random.random() < 0.5  # 50/50 mix

        if is_simple:
            text = random.choice(simple_templates)
            # Add some random variation to avoid identical deduping if that's a thing
            text += f" ( {random.randint(100, 999)} )"
        else:
            text = random.choice(complex_templates)
            text += f" - Analysis ID: {random.randint(1000, 9999)}"

        message = {
            "id": i,
            "text": text,
            "ocr_text": "",  # Simulating text-only for now as per "0.6s latency" context usually implies text
            "date": "2024-01-01 12:00:00",
        }
        dataset.append(message)

    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"Generated {count} messages to {output_path}")


if __name__ == "__main__":
    generate_stress_dataset()
