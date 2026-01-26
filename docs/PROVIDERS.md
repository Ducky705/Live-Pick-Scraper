# AI Providers & Smart Cascading Strategy

CapperSuite utilizes a **"Complexity Router"** strategy (Smart Cascading) to balance Accuracy, Efficiency, and Speed. Instead of a simple round-robin, models are tiered by cost and speed.

## The Hierarchy

### Tier 1: The "Speedsters" (High Speed, Low Cost)
*   **Primary:** **Gemini 2.0 Flash Lite**
*   **Secondary:** **Cerebras (Llama-3.1-8b)**
*   **Role:** "Gatekeeper". Handles 80% of traffic (filtering junk, parsing simple standard lines).
*   **Characteristics:** Extremely high throughput, very low cost.

### Tier 2: The "Experts" (High Accuracy)
*   **Primary:** **Groq (Llama-3.3-70b)**
*   **Secondary:** **Mistral Large**
*   **Role:** "Heavy Lifter". Handles complex bets (props, parlays), images (Vision), and **retries** from Tier 1.
*   **Characteristics:** High intelligence, stricter rate limits.

### Tier 3: The "Safety Net"
*   **Primary:** **OpenRouter / Gemini Pro**
*   **Role:** Emergency failover if Tier 1 and Tier 2 are exhausted or failing.

## Logic Flow

```mermaid
graph TD
    A[Incoming Batch] --> B{Contains Image?}
    B -- Yes --> C[Tier 2: Groq Vision / Mistral]
    B -- No --> D{Text Length > 3000 chars?}
    D -- Yes --> E[Tier 2: Groq Llama-70b]
    D -- No --> F[Tier 1: Gemini Flash Lite / Cerebras]
    F --> G{Valid JSON & High Confidence?}
    G -- Yes --> H[Save Result]
    G -- No/Error --> E[Escalate to Tier 2: Groq (Retry)]
```

## Supported Providers & Config

| Provider | Tier | Role | Models | Status |
|----------|------|------|--------|--------|
| **Gemini** | 1 | Primary Speed | `gemini-2.0-flash-lite` | **ACTIVE** |
| **Cerebras** | 1 | Secondary Speed | `llama-3.1-8b` | **ACTIVE** |
| **Groq** | 2 | Primary Expert | `llama-3.3-70b` | **ACTIVE** |
| **Mistral** | 2 | Secondary Expert | `codestral`, `pixtral` | Active |
| **OpenRouter**| 3 | Fallback | Various | Backup |

## Rate Limit Strategy (Smart Circuit Breaker)

- **Circuit Breaker:** If a provider hits `429` (Rate Limit) 3 times consecutively, it is suspended for 60s.
- **Spillover:** If Tier 1 is saturated, traffic spills to Tier 2.
- **Pre-flight Check:** Local token estimation prevents sending requests that would definitely fail known TPM limits.
