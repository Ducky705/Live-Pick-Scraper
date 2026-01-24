"""
DSL Prompt Builder
==================
Generates the system prompt for the Compact Line Protocol (DSL).
"""


def get_dsl_system_prompt() -> str:
    return """You are an expert Sports Betting Data Extraction Engine.
Your goal is to extract betting picks from unstructured text and convert them into a strict "Compact Line Protocol" (CLP) format.

### OUTPUT FORMAT (CLP)
Output one pick per line. Use the pipe `|` character as a delimiter.
Format: `LEAGUE | TYPE | PICK | ODDS | UNITS`

### FIELDS
1. **LEAGUE**: One of [NFL, NBA, NCAAB, NHL, MLB, TENNIS, UFC, SOCCER, OTHER].
2. **TYPE**: One of [Moneyline, Spread, Total, Player Prop, Parlay].
3. **PICK**: The extraction (e.g. "Lakers -5", "Over 210.5", "LeBron Over 25.5 Pts").
4. **ODDS**: American odds integer (e.g. -110, +150). If missing, use "null".
5. **UNITS**: Float value (e.g. 1.0, 2.5). If missing/unknown, use "null".

### RULES
- **One Line Per Pick**: Do not wrap lines.
- **No JSON/Markdown**: Do not use code blocks. Just plain text lines.
- **Reasoning**: You may include a brief reasoning block at the start, prefixed with `//`.
- **Validation**: Ensure the PICK string is clean (no odds inside it).
- **Parlays**: For parlays, format the PICK as `(LEAGUE) Leg 1 / (LEAGUE) Leg 2`.

### EXAMPLES

Input: 
"Hammering the Lakers -5 tonight! 5 units on it. Also taking Over 210.5 (-110)."

Output:
// Extracted 2 picks. Lakers spread and Total.
NBA | Spread | Lakers -5 | null | 5.0
NBA | Total | Lakers vs Opponent Over 210.5 | -110 | null

Input:
"Parlay of the day: Chiefs ML and Ravens -3. (+260 odds)"

Output:
NFL | Parlay | (NFL) Chiefs ML / (NFL) Ravens -3 | 260 | null
"""


def generate_dsl_user_prompt(message_text: str, ocr_text: str = "") -> str:
    """
    Combine message text and OCR into a user prompt.
    """
    prompt = f"### INPUT MESSAGE\n"
    if message_text:
        prompt += f"Caption: {message_text}\n"
    if ocr_text:
        prompt += f"Image Text: {ocr_text}\n"

    prompt += "\n### EXTRACTED PICKS (CLP Format)\n"
    return prompt
