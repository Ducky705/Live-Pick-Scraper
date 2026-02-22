# Prompt System Documentation

The CapperSuite v3.6 Prompt System is designed for **maximum token efficiency** and cost reduction. It employs a compact JSON schema and automated decoding to minimize the LLM context window usage.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PROMPT / DECODER FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │   RAW    │──▶│   LLM    │───▶│ COMPACT  │──▶│ DECODER  │───▶│ EXPANDED │   │
│  │  PROMPT  │    │ PROVIDER │    │   JSON   │    │  MODULE  │    │  OBJECT  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                        │                                        │
│                                        ▼                                        │
│                                  ┌──────────┐                                   │
│                                  │ {"c":"K",│                                   │
│                                  │  "l":"N"}│                                   │
│                                  └──────────┘                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Compact Schema

To reduce output tokens (and latency), the prompt instructs the LLM to use single-character keys and abbreviated values.

### Key Mapping (`src/prompts/decoder.py`)

| Key | Full Name | Description |
|-----|-----------|-------------|
| `i` | `message_id` | Unique ID of the source message |
| `c` | `capper_name` | Name of the handicapper |
| `l` | `league` | League code (NBA, NFL, etc.) |
| `t` | `type` | Bet type abbreviation |
| `p` | `pick` | The actual pick text |
| `o` | `odds` | American odds (e.g., -110) |
| `u` | `units` | Unit size (confidence) |
| `r` | `reasoning` | Optional reasoning text |

### Type Abbreviations

| Abbreviation | Full Type |
|--------------|-----------|
| `ML` | Moneyline |
| `SP` | Spread |
| `TL` | Total |
| `PP` | Player Prop |
| `TP` | Team Prop |
| `GP` | Game Prop |
| `PD` | Period |
| `PL` | Parlay |
| `TS` | Teaser |
| `FT` | Future |

## Components

### 1. Prompt Builder (`src/prompt_builder.py`)
Constructs the optimized system prompt. It dynamically includes:
- The compact schema definition.
- OCR text from images.
- Message context.

### 2. Decoder (`src/prompts/decoder.py`)
Responsible for expanding the compact AI response back into a developer-friendly format.

**Key Functions:**
- `normalize_response(text)`: Extracts JSON from markdown/text and expands keys.
- `expand_picks_list(list)`: Batch expansion of picks.
- `expand_compact_pick(dict)`: Expands a single pick object.

## Example

**LLM Output:**
```json
{
  "picks": [
    {
      "i": 101,
      "c": "Sharp",
      "l": "NBA",
      "t": "SP",
      "p": "Lakers -5",
      "o": -110
    }
  ]
}
```

**After Decoding:**
```json
[
  {
    "message_id": 101,
    "capper_name": "Sharp",
    "league": "NBA",
    "type": "Spread",
    "pick": "Lakers -5",
    "odds": -110,
    "units": 1.0
  }
]
```

## Benefits

1.  **Cost Reduction**: ~50% fewer output tokens.
2.  **Speed**: Faster generation times (less text to generate).
3.  **Reliability**: Simpler structure reduces JSON syntax errors.

## Advanced Reasoning Architectures (v3.6+)

To achieve high extraction accuracy (~81%) on extremely fast, cost-effective "non-reasoning" LLMs (like `stepfun/step-3.5-flash`), we employ two advanced prompt formatting techniques inspired by modern LLM telemetry extraction research.

### 1. Double Prompting
Instead of sending a single query to the model, the exact same prompt block is concatenated to itself before submission (e.g., `<PROMPT>\n\n<PROMPT>`). This heavily biases the model's attention mechanism toward the constraints and instructions, dramatically lowering hallucination rates on smaller models without increasing generation latency.

### 2. Explicit XML Reasoning (Chain of Thought)
We force the model to explicitly reason through the extraction process *before* it generates the final JSON. The model is instructed to output a `<thinking>...</thinking>` block to execute a mandatory 4-step sequence on every message:
1. **Denoising and Triage**: Separate the bet from the marketing text.
2. **Entity Translation**: Translate shorthand (e.g. BTTS, 5U).
3. **Schema Mapping**: Map values to the JSON keys mentally.
4. **Null Value Verification**: Guard against hallucinating missing data.

By decoupling the chaotic classification layer from the strict JSON payload generation, the models correctly predict edge cases while maintaining flawless JSON syntax. 

*(Note: Experiments involving absolute zero Thermodynamic Calibration (`temperature=0.0`) and Multi-Layer Task-Aware Prompt Chaining (Binary triage) were tested but reverted as they decreased overall recall on complex, multi-pick messages).*
