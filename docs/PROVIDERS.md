# AI Providers & Smart Cascading Strategy

CapperSuite utilizes a **"Complexity Router"** strategy (Smart Cascading) to balance Accuracy, Efficiency, and Speed. Instead of a simple round-robin, models are tiered by cost, speed, and proven robustness.

## The Hierarchy (Scientifically Optimized)

### Tier 1: The "Speedsters" (High Speed, Free)
*   **Primary:** **Cerebras (Llama-3.1-8b)**
    *   **Status:** **CHAMPION**. Proven most robust for parallel concurrency (4 workers).
*   **Secondary:** **Groq (Llama-3.1-8b-Instant)**
    *   **Status:** **FASTEST**. Sub-second latency, but strictly rate-limited (429s).
*   **Role:** "Gatekeeper". Handles 90% of traffic.
*   **Strategy:** **Batch Size 1**. Processing single messages to prevent hallucination (The "Fast but Dumb" fix).

### Tier 2: The "Quality Fallback" (High Accuracy)
*   **Primary:** **Mistral (Codestral/Small)**
*   **Secondary:** **OpenRouter (DeepSeek R1 / Llama-3.3-70b)**
*   **Role:** "Heavy Lifter". Activated **ONLY** when Tier 1 fails quality checks (e.g., missing `capper` name) or hits Rate Limits.
*   **Characteristics:** slower (~2-3s) but 100% accurate on complex data.

### Tier 3: The "Safety Net"
*   **Primary:** **Gemini 2.0 Flash Lite**
*   **Role:** Emergency failover if specific Llama models are unavailable.

## Logic Flow

```mermaid
graph TD
    A[Incoming Queue] -->|Concurrency Limit: 4| B{Is Image?}
    B -- Yes --> C[Tier 2: Mistral / Vision]
    B -- No --> D[Tier 1: Cerebras / Groq 8b]
    D --> E{Quality Check Passed?}
    E -- Yes --> F[Save Result (~0.8s)]
    E -- No/429 --> G[Tier 2: OpenRouter/Mistral Fallback]
    G --> H[Save Result (~2.6s)]
```

## Configuration Constants

These values were determined via iterative benchmarking (Iterations 1-50):

| Setting | Value | Reason |
|---------|-------|--------|
| **Batch Size** | `1` | 8b models hallucinate when processing >1 message at once. |
| **Concurrency** | `4` | Sweet spot. >4 triggers cascading Rate Limits on Free Tiers. |
| **Timeout** | `25s` | Allows for 1 retry + Fallback execution time. |

## Supported Providers & Config

| Provider | Tier | Role | Models | Status |
|----------|------|------|--------|--------|
| **Cerebras** | 1 | Primary Speed | `llama-3.1-8b` | **ACTIVE** |
| **Groq** | 1 | Secondary Speed | `llama-3.1-8b-instant` | **ACTIVE** |
| **Mistral** | 2 | Quality Backup | `codestral` | **ACTIVE** |
| **OpenRouter**| 2 | Heavy Backup | `deepseek-r1`, `llama-3.3-70b` | **ACTIVE** |
| **Gemini** | 3 | Emergency | `gemini-2.0-flash` | Backup |

## Rate Limit Strategy (Smart Circuit Breaker)

- **Circuit Breaker:** If a provider hits `429` (Rate Limit) 3 times consecutively, it is suspended for 60s.
- **Queue Wait:** If Tier 1 is busy, workers **WAIT** (up to 2s) for a slot rather than failing over immediately to expensive tiers.
- **Fail-Over:** Automatic escalation to Tier 2 on specific errors (JSONDecodeError, MissingKeyError).
