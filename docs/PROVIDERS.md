# AI Providers & Parallel Processing

CapperSuite utilizes a multi-provider strategy to parse betting picks with maximum speed and reliability. The system is designed to handle rate limits, failures, and varying model capabilities.

## Supported Providers

| Provider | Client File | Role | Models | Status |
|----------|-------------|------|--------|--------|
| **Groq** | `src/groq_client.py` | Primary Parser | `llama-3.3-70b` | **RECOMMENDED** |
| **Mistral** | `src/mistral_client.py` | Secondary / Vision | `codestral`, `pixtral` | Excellent |
| **Gemini** | `src/gemini_client.py` | Backup | `gemini-2.5-flash` | Good |
| **Cerebras** | `src/cerebras_client.py` | Overflow | `llama3.1-8b` | Fast, Text-only |
| **OpenRouter** | `src/openrouter_client.py` | Fallback | Various | Slow |

## Parallel Batch Processor

The `ParallelBatchProcessor` (`src/parallel_batch_processor.py`) orchestrates the distribution of work across these providers.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PARALLEL BATCH PROCESSOR                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ INCOMING │───▶│  BATCH   │───▶│   LOAD   │───▶│ WORKER   │───▶│ PROVIDER │   │
│  │ MESSAGES │    │ SPLITTER │    │ BALANCER │    │  POOL    │    │   API    │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                        │               │                        │
│                                        ▼               │                        │
│                                  ┌──────────┐          ▼                        │
│                                  │ RATE LMT │    ┌──────────┐    ┌──────────┐   │
│                                  │ MONITOR  │    │ 16x GROQ │    │ 4x MISTR │   │
│                                  └──────────┘    └──────────┘    └──────────┘   │
│                                                        │               │        │
│                                                  ┌──────────┐    ┌──────────┐   │
│                                                  │  3x GEM  │    │  2x CER  │   │
│                                                  └──────────┘    └──────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Strategy (Maximum Speed)

The system aims for **25 concurrent workers** to maximize throughput:

1.  **Groq (16 workers)**: Handles 64% of the load. 1000 requests/minute limit allows high concurrency.
2.  **Mistral (4 workers)**: Handles 16%. Supports high token limits (500K TPM), allowing efficient batching.
3.  **Gemini (3 workers)**: Handles 12%.
4.  **Cerebras (2 workers)**: Handles 8%.

### Features

-   **Rate Limit Awareness**: Tracks RPM (Requests Per Minute) and TPM (Tokens Per Minute) for each provider.
-   **Smart Backoff**: Automatically sleeps if rate limits are hit.
-   **Failover**: If a primary provider fails, the batch is retried with a fallback provider.
-   **Load Balancing**: Distributes batches round-robin based on provider capacity.

## Configuration

Provider settings are defined in `src/parallel_batch_processor.py` (constant `PROVIDER_CONFIG`):

```python
PROVIDER_CONFIG = {
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "rpm": 1000,
        "max_concurrent": 16,
        "priority": 1,
    },
    # ...
}
```

To enable a provider, ensure its API key is set in the `.env` file (`GROQ_TOKEN`, `MISTRAL_TOKEN`, etc.). The processor automatically detects available providers.
