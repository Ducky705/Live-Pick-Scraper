import json
import time

import requests

REPO_OWNER = "Ducky705"
REPO_NAME = "Telegram-Scraper"
TOKEN = "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"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"

headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

# The "Billion Dollar" Release Metadata
releases_metadata = [
    {
        "tag_name": "v0.1.0",
        "name": "v0.1.0",
        "body": "### Foundation\n\nInitial repository initialization and structural cleanup. Established the baseline architecture for the scraper engine.\n\n- **Project Structure**: Standardized directory layout.\n- **Hygiene**: comprehensive `.gitignore` and asset cleanup.",
    },
    {
        "tag_name": "v0.2.0",
        "name": "v0.2.0",
        "body": "### System Visibility\n\nIntroduced comprehensive architecture visualizations to transparently map data flow and system components.\n\n- **Mermaid Diagrams**: Added dynamic flowcharts for the scraping pipeline.\n- **Documentation**: Initial system architecture overview.",
    },
    {
        "tag_name": "v1.0.0",
        "name": "v1.0.0",
        "body": "### The Desktop App\n\n**The first stable release of the standalone Desktop GUI.**\n\nWe have packaged the power of the scraper into a user-friendly application for macOS and Windows.\n\n#### Features\n- **Native App**: Standalone executable with no external dependencies.\n- **Authentication**: Secure user login and session management.\n- **Local OCR**: Bundled OCR engine for offline image processing.",
    },
    {
        "tag_name": "v1.0.1",
        "name": "v1.0.1",
        "body": "### Patch 1.0.1\n\nStability improvements for the Desktop App.\n\n- **Auto-Update**: Silent background update mechanism.\n- **Network Resilience**: Added retry logic for unstable API connections on macOS.",
    },
    {
        "tag_name": "v1.1.0",
        "name": "v1.1.0",
        "body": "### Intelligence Hub\n\nMajor upgrades to the optical character recognition (OCR) pipeline and performance analytics.\n\n#### Core Updates\n- **Advanced Preprocessing**: New contrast enhancement and noise reduction algorithms for betting slips.\n- **Benchmarking Suite**: Tools to measure and visualize OCR accuracy against ground truth datasets.",
    },
    {
        "tag_name": "v1.2.0",
        "name": "v1.2.0",
        "body": "### UX Refinement\n\nPolishing the interaction model for manual reviews.\n\n- **AI Review Interface**: Completely redesigned UI for verifying AI predictions.\n- **Performance**: Optimized main thread handling for smoother loading states.",
    },
    {
        "tag_name": "v2.0.0",
        "name": "v2.0.0",
        "body": "### Grading Engine V2\n\n**Automated result verification with real-time sports data.**\n\nThis release introduces the V2 Grading Engine, allowing the system to automatically determine if a pick won or lost.\n\n#### New Capabilities\n- **Multi-Sport Support**: Added logic for NBA, NFL, NHL, and NCAAB.\n- **ESPN Integration**: Direct high-speed connection to ESPN's real-time score APIs.\n- **Prop Logic**: Enhanced handling for player performance double-doubles and stat milestones.",
    },
    {
        "tag_name": "v3.0.0",
        "name": "v3.0.0",
        "body": "### AI Core Classification\n\n**Smart noise filtering powered by Large Language Models.**\n\nWe've integrated an AI classification layer before the parsing pipeline to reduce costs and improve signal-to-noise ratio.\n\n#### Features\n- **Auto-Classification**: Distinguishes between Picks, Promos, Recaps, and General Chat.\n- **Cost Efficiency**: Reduces LLM usage by filtering irrelevant messages upstream.\n- **Signal Purity**: Only forwards high-confidence betting content to the parser.",
    },
    {
        "tag_name": "v3.1.0",
        "name": "v3.1.0",
        "body": '### The Final GUI Milestone\n\nThe ultimate refinement of the Desktop architecture before our shift to high-performance infrastructure.\n\n#### Improvements\n- **Parallel OCR**: Concurrent image processing for multi-image posts.\n- **Two-Pass Verification**: A secondary AI "Auditor" to verify extracted data accuracy.',
    },
    {
        "tag_name": "v3.1.1",
        "name": "v3.1.1",
        "body": "### Logic Patch\n\n- **Chimera Confidence**: Implemented multi-model voting logic for ambiguous edge cases.\n- **Conflict Resolution**: Heuristics for resolving disagreements between OCR and LLM outputs.",
    },
    {
        "tag_name": "v4.0.0",
        "name": "v4.0.0",
        "body": "## \u26a0\ufe0f The CLI Evolution\n\n**This is a breaking change. The GUI has been retired.**\n\nWe have completely re-architected the system as a professional Command Line Interface (CLI) tool. This pivot enables headless server deployment, massive concurrency, and pipeline automation.\n\n#### The Shift\n- **Headless Architecture**: No more GUI overhead. Designed for cron jobs and servers.\n- **Pipeline Focus**: Streamlined specific pipelines for Scrape \u2192 Parse \u2192 Grade \u2192 Export.\n- **Developer First**: Configuration via `.env` and simple CLI flags.",
    },
    {
        "tag_name": "v4.1.0",
        "name": "v4.1.0",
        "body": "### Vision Engine Upgrade\n\nReplacing legacy OCR with deep learning for superior accuracy.\n\n#### RapidOCR Integration\n- **Engine**: Switched from Tesseract to **RapidOCR (ONNX)**.\n- **Performance**: Accuracy jumped from ~60% to **93%**.\n- **Robustness**: Native handling of dark mode screenshots and stylized betting slips.",
    },
    {
        "tag_name": "v4.1.1",
        "name": "v4.1.1",
        "body": "### Market Strictness\n\nEnforcing rigorous data standards for complex bet types.\n\n- **Tennis Support**: Specialized parsers for Set/Game spreads.\n- **Parlay Enforcement**: Strict validation rules for multi-leg accumulators.\n- **Period Detection**: Enhanced logic for 1st Half, 1st Quarter, and First 5 Innings markets.",
    },
    {
        "tag_name": "v4.2.0",
        "name": "v4.2.0",
        "body": "### Grading Engine V3\n\n**A complete rewrite of the result verification system.**\n\nWe rebuilt the grader from scratch to eliminate false positives and support the full spectrum of betting markets.\n\n#### Key Changes\n- **Modular Architecture**: Decoupled parsing, matching, and scoring logic for easier maintenance.\n- **Strict Matching**: Zero-tolerance algorithm for team name matching.\n- **Alias Database**: Expanded team dictionary to 500+ variations.",
    },
    {
        "tag_name": "v4.3.0",
        "name": "v4.3.0",
        "body": "### High Throughput\n\n**Unlocking maximum concurrency.**\n\n- **25 Concurrent Workers**: Parallelized the pipeline across Groq, Mistral, and Gemini providers.\n- **Rate Limit Optimization**: Smart semaphore management to maximize API usage without 429 errors.\n- **Groq-First Routing**: 80% of traffic is now routed to sub-second latency models.",
    },
    {
        "tag_name": "v4.4.0",
        "name": "v4.4.0",
        "body": "### Efficiency & Cost\n\n**Doing more with less.**\n\n- **Compact Schema**: Reduced JSON output tokens by **50%**.\n- **Prompt Engineering**: Compressed system prompts by **67%** without accuracy loss.\n- **Auto-Decoder**: Transparent utility to expand compact responses into full objects downstream.",
    },
    {
        "tag_name": "v4.5.0",
        "name": "v4.5.0",
        "body": "### Architecture Restructure\n\nPreparing the codebase for scale.\n\n- **Source Organization**: Consolidated all application logic into `src/`.\n- **Data Isolation**: Runtime data (logs, cache, sessions) moved to `data/`.\n- **Documentation Center**: All technical docs centralized in `docs/`.",
    },
    {
        "tag_name": "v4.6.0",
        "name": "v4.6.0",
        "body": "### Stability & Performance\n\n**The fastest version of CapperSuite yet.**\n\n- **Persistent Caching**: SQLite-backed caching for ESPN Scores (24h TTL) and Boxscores (7d TTL).\n- **Connection Pooling**: Reusable TCP connections for API requests.\n- **Results**: Grading process is now **6.3x faster**.",
    },
    {
        "tag_name": "v4.6.1",
        "name": "v4.6.1",
        "body": "### Polish\n\nFinal touches on the v4.x series.\n\n- **Documentation**: Corrected data flow arrows in architecture diagrams.\n- **Cleanup**: Removed unused imports and legacy configuration files.",
    },
]


def update_releases():
    print("Fetching existing releases...")
    existing_releases = []
    page = 1
    while True:
        resp = requests.get(f"{API_URL}?page={page}&per_page=100", headers=headers)
        if resp.status_code != 200:
            print(f"Error fetching: {resp.status_code}")
            break
        data = resp.json()
        if not data:
            break
        existing_releases.extend(data)
        page += 1

    tag_map = {r["tag_name"]: r["id"] for r in existing_releases}
    print(f"Found {len(existing_releases)} existing releases.")

    for meta in releases_metadata:
        tag = meta["tag_name"]
        if tag in tag_map:
            release_id = tag_map[tag]
            print(f"Updating {tag}...")
            payload = {"name": meta["name"], "body": meta["body"]}
            requests.patch(f"{API_URL}/{release_id}", headers=headers, data=json.dumps(payload))
            time.sleep(0.5)


if __name__ == "__main__":
    update_releases()
