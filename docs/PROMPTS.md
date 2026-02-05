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
