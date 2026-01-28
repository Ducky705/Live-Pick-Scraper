# Product Requirements Document (PRD)
## Project: High-Performance Telegram Extraction Pipeline
**Version:** 1.3
**Status:** Active

---

### 1. Executive Summary
This project aims to build a robust, high-performance extraction pipeline capable of processing real-time betting tips from Telegram channels. The system prioritizes accuracy (non-negotiable) while optimizing for speed and cost-efficiency via a multi-provider strategy (Cerebras, Groq, Mistral).

### 2. Objectives
*   **Reliability:** Zero "Death Spirals" due to rate limits.
*   **Latency:** p95 < 2s for standard picks.
*   **Accuracy:** 100% Recall on Golden Set.

---

### 3. User Stories

### US-001: Adaptive Concurrency Control
**As a** System Architect,
**I want** the system to automatically throttle worker threads when 429 Rate Limits occur,
**So that** we prevent "Death Spirals" and avoid temporary bans from Free Tier providers.

**Acceptance Criteria:**
- [ ] System starts at `MAX_CONCURRENCY` (Default: 4).
- [ ] Upon receiving a `429` error, concurrency immediately drops by 50% (min 1).
- [ ] System logs a "Backoff Warning" event with current worker count.
- [ ] After 10 consecutive successful requests, concurrency increments by 1 (up to MAX).
- [ ] **Verify:** Simulated stress test with forced 429s triggers backoff logic.

### US-002: Latency Budget Enforcement
**As an** End User,
**I want** requests to fail fast if they hang, but allow enough time for quality fallbacks,
**So that** the pipeline maintains throughput without blocking on zombie processes.

**Acceptance Criteria:**
- [ ] **Tier 1 (Speed) Target:** < 5.0s soft limit.
- [ ] **Tier 2 (Quality) Target:** < 20.0s soft limit.
- [ ] **Global Hard Timeout:** 25.0s. Requests exceeding this are killed immediately.
- [ ] Timeout events are logged as "Timeout Failure" (distinct from API Error).
- [ ] **Verify:** A hanging provider mock does not block the batch indefinitely.

### US-003: Dynamic Confidence Thresholding
**As a** Data Analyst,
**I want** the system to force AI validation for "High Confidence" regex picks if context keywords (e.g., "Parlay") are present,
**So that** complex bets aren't missed by simple rules.

**Acceptance Criteria:**
- [ ] Implement "Context Scanner" for keywords: `Parlay`, `Teaser`, `If Bet`, `Chain`.
- [ ] Logic: `IF (RegexScore > 8.5) AND (ContextHasKeywords) THEN Force AI`.
- [ ] **Verify:** A message with 1 regex pick but text "Parlay" triggers AI refinement.
- [ ] Recall on Golden Set must exceed 95%.

### US-004: Golden Set Expansion
**As a** QA Engineer,
**I want** the regression test suite to include the identified "15% Gap" edge cases,
**So that** optimizations do not cause regressions on complex messages.

**Acceptance Criteria:**
- [ ] Add 5 new "Complex" messages to `new_golden_set.json` (Multi-sport, Teasers).
- [ ] **Verify:** `verify_golden_set.py` runs with 100% success.
- [ ] **Verify:** No regression on existing simple messages.

---

### 4. Non-Functional Requirements
*   **Infrastructure:** Standard consumer hardware (8GB RAM, 4 vCPUs). No local GPU.
*   **Cost:** $0.00 operational cost (Free Tiers only).
*   **Security:** API Keys managed via `.env`. No hardcoded secrets.
