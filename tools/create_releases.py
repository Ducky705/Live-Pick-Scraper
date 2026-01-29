import json
import time

import requests

REPO_OWNER = "Ducky705"
REPO_NAME = "Telegram-Scraper"
TOKEN = "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"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"

headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

releases = [
    {
        "tag_name": "v0.1.0",
        "name": "v0.1.0 - Foundation",
        "body": "**Foundation**\nInitial repository cleanup and professional structure.",
    },
    {
        "tag_name": "v0.2.0",
        "name": "v0.2.0 - Visibility",
        "body": "**Visibility**\nAdded comprehensive Mermaid architecture diagrams.",
    },
    {
        "tag_name": "v1.0.0",
        "name": "v1.0.0 - The Launch",
        "body": "**FIRST STABLE RELEASE**\nStandalone Desktop GUI (Win/Mac) with Auth/OCR.",
    },
    {"tag_name": "v1.0.1", "name": "v1.0.1 - Patch", "body": "**Patch**\nSilent auto-update and API retry logic."},
    {
        "tag_name": "v1.1.0",
        "name": "v1.1.0 - Intelligence",
        "body": "**Intelligence Hub**\nAdvanced OCR preprocessing and benchmarking tools.",
    },
    {
        "tag_name": "v1.2.0",
        "name": "v1.2.0 - UX",
        "body": "**User Experience**\nRedesigned AI Review UI and loader smoothness.",
    },
    {
        "tag_name": "v2.0.0",
        "name": "v2.0.0 - Grading",
        "body": "**MAJOR: Grading Engine V2**\nIntroduced Multi-Sport support and ESPN API integration.",
    },
    {
        "tag_name": "v3.0.0",
        "name": "v3.0.0 - AI Core",
        "body": "**MAJOR: AI Core**\nFirst implementation of AI Auto-Classification (Promo/Recap detection).",
    },
    {
        "tag_name": "v3.1.0",
        "name": "v3.1.0 - Final GUI",
        "body": "**Peak GUI Milestone**\nFinal major update for the Desktop interface. Parallel OCR & Two-Pass Verification.",
    },
    {
        "tag_name": "v3.1.1",
        "name": "v3.1.1 - Logic",
        "body": "**Logic Patch**\nAdded Two-Pass Confidence System ('Chimera' logic).",
    },
    {
        "tag_name": "v4.0.0",
        "name": "v4.0.0 - THE CLI EVOLUTION",
        "body": "# 🚀 THE CLI EVOLUTION\n\n**BREAKING CHANGE**: Removed GUI entirely.\n\nTransitioned to a professional-grade CLI-only architecture for high-performance scraping.",
    },
    {
        "tag_name": "v4.1.0",
        "name": "v4.1.0 - Vision",
        "body": "**Vision Update**\nIntegration of RapidOCR (Deep Learning Engine). 93% avg confidence.",
    },
    {
        "tag_name": "v4.1.1",
        "name": "v4.1.1 - Market Fix",
        "body": "**Market Support**\nStrict format enforcement for Tennis and Parlay markets.",
    },
    {
        "tag_name": "v4.2.0",
        "name": "v4.2.0 - Scale",
        "body": "**Grading Engine V3**\nComplete rewrite of the grading logic. Eliminated false positives.",
    },
    {
        "tag_name": "v4.3.0",
        "name": "v4.3.0 - Throughput",
        "body": "**Performance**\nRate limit optimization (25 concurrent workers).",
    },
    {
        "tag_name": "v4.4.0",
        "name": "v4.4.0 - Efficiency",
        "body": "**Efficiency**\nCompact Prompt Schema (-67% token usage per message).",
    },
    {
        "tag_name": "v4.5.0",
        "name": "v4.5.0 - Structure",
        "body": "**Architecture**\nFull project restructuring. Runtime data moved to `data/`.",
    },
    {
        "tag_name": "v4.6.0",
        "name": "v4.6.0 - Stability",
        "body": "**Performance Milestone**\nIntroduced Persistent SQLite Caching & Connection Pooling.",
    },
    {
        "tag_name": "v4.6.1",
        "name": "v4.6.1 - Polish",
        "body": "**Polish**\nFinal documentation, diagram, and arrow direction fixes.",
    },
]

print(f"Creating {len(releases)} releases...")

for release in releases:
    data = {
        "tag_name": release["tag_name"],
        "name": release["name"],
        "body": release["body"],
        "draft": False,
        "prerelease": False,
    }

    response = requests.post(API_URL, headers=headers, data=json.dumps(data))

    if response.status_code == 201:
        print(f"[OK] Created {release['tag_name']}")
    elif response.status_code == 422:
        print(f"[SKIP] {release['tag_name']} already exists")
    else:
        print(f"[FAIL] Failed {release['tag_name']}: {response.status_code} - {response.text}")

    time.sleep(1)  # Rate limit safety

print("Done!")
