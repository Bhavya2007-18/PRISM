# PRISM — Project History

> Complete record of what was built, when, and why.
> This is the authoritative source of truth for the project's evolution.

---

## Origin

**Project:** PRISM — Polyglot Real-time Intelligent Support Mediator
**Hackathon:** EchoSphere: Agora Conversational AI Hackathon
**Problem Statement:** PS51 — Multilingual Assistance-Line Agent with Human Escalation
**Core requirement:** Agora must be the real-time voice infrastructure, not an afterthought.

---

## Phase 1 — Project Scaffolding

**What was built:**
- Full project structure: `frontend/` (Vite + React) and `backend/` (FastAPI)
- All dependency files: `requirements.txt`, `frontend/package.json`
- Environment variable templates: `.env.example`, `.gitignore`
- Minimal runnable stubs for both services
- `/health` endpoint returning `{"status": "ok"}`

**Why:** Established a clean foundation before writing any feature code. Both processes needed to start without errors before anything else could be built.

---

## Phase 2 — Agora RTC Token Server & Channel Join

**What was built:**
- `GET /token?channel={name}&uid={uid}` — RTC token generation using `agora_token_builder`
- `VoiceInterface.jsx` — Agora Web SDK integration: `createClient`, `join`, `createMicrophoneAudioTrack`, `publish`, `user-published` event handler to play agent audio
- Demo mode fallback when no Agora credentials are configured
- Connection status states: idle / connecting / connected / error

**Why:** The voice loop only works if the browser can join an Agora channel and publish mic audio. This was the prerequisite for everything else.

---

## Phase 3 — Agora Conversational AI Agent Start/Stop

**What was built:**
- `POST /session/start` — calls the Agora Conversational AI v2 REST API (`POST /agents/start`) with the LLM proxy URL, tool schemas, TTS vendor, ASR language config
- `POST /session/stop` — stops the Agora agent
- Backend generates a separate RTC token for the agent UID (12345)
- Agent uses Agora native TTS (`vendor: "agora"`, `voice_id: "female-south-asian-en"`)
- Greeting message: "Namaste! Main PRISM hoon. Aap kaise help kar sakta hoon?"
- Frontend calls `/session/start` after joining the channel

**Why:** The Agora Conversational AI Engine is what gives PRISM its real-time voice capability. The agent joins the channel as a virtual participant and handles STT + LLM + TTS in Agora's cloud — PRISM only needs to provide the LLM endpoint URL.

---

## Phase 4 — Structured Case State & Decision Engine

**What was built:**
- `backend/context.py` — `CaseState` dataclass with all fields (intent, transaction_id, amount, payment_status, order_status, duplicate_charge, language, verified, unverified, conversation_history, etc.)
- `backend/decision.py` — deterministic `decide(case)` function: priority-ordered rules returning `Action.ASK / TOOL_CALL / ESCALATE / RESOLVE`
- `backend/confidence.py` — `FieldConfidence` enum (HIGH / LOW / CRITICAL_UNKNOWN) + `get_confidence_report()`
- `backend/tools.py` — `check_transaction()` mock, `create_escalation_ticket()`, `ALL_TOOLS` OpenAI function schema

**Why:** PRISM's core differentiator — the LLM handles language, code handles decisions. The decision engine is pure Python with no LLM calls, making it deterministic, auditable, and impossible to hallucinate.

---

## Phase 5 — LLM Proxy & PRISM Intelligence

**What was built:**
- `POST /llm-proxy` — receives OpenAI-format requests from Agora, intercepts tool calls, executes them locally, feeds results back
- `POST /chat` — text-mode equivalent using the same intelligence layer
- `<EXTRACT>` block protocol: LLM appends a structured JSON block after every response; backend strips it and updates case state
- Deterministic fallback: when LLM is unavailable, `_run_deterministic_path()` produces honest Hindi replies
- LLM response validation: detects error text in LLM responses and falls back

**Architecture established:**
```
Agora → /llm-proxy → voice_agent.run_agent_turn()
                         ├── LLM (language + proposals)
                         ├── Tool execution (deterministic)
                         └── Policy gate (deterministic escalation authority)
```

**Why:** The LLM proxy is the bridge between Agora's cloud STT→LLM loop and PRISM's structured decision layer. By controlling this layer, PRISM can inject case context, intercept tool calls, and validate escalation proposals before they take effect.

---

## Phase 6 — Confidence Engine & Escalation

**What was built:**
- Label-based confidence: HIGH (tool-verified) / LOW (user-stated) / CRITICAL_UNKNOWN (absent)
- Display score mapping for UI: HIGH=95%, LOW=55%, CRITICAL_UNKNOWN=41%
- Multi-condition escalation triggers: missing critical info, contradiction, tool failure, low confidence, explicit user request
- `_trigger_escalation()` — creates structured ticket, stores in `escalated_cases`
- Escalation summary with all verified/unverified fields, reason, confidence

**Design decision:**
> Confidence is a label, not a magic number. HIGH/LOW/CRITICAL_UNKNOWN is honest. The display percentage (41%) is a UI convenience, not a calibrated probability.

**Why:** The hackathon spec required PRISM to "know when it doesn't know enough." Labelled confidence with deterministic escalation triggers achieves this honestly without pretending the system has more certainty than it does.

---

## Phase 7 — Human Agent Dashboard

**What was built:**
- `GET /cases` — returns all escalated cases
- `POST /cases/{case_id}/takeover` — marks a case taken over, updates live state
- `Agent.jsx` — full 3-column dashboard: cases sidebar, live conversation, case intelligence panel
- `EscalationPanel.jsx` — case card with verified/uncertain fields, confidence bar, Take Over button
- `CasePanel.jsx` — structured case intelligence display
- Live 2-second polling of `/cases` and `/active-state`
- Agora channel join for human agent (UID 88888) on takeover

**Why:** Context-preserving human handoff is the "money shot" of the demo. The human agent receives a structured case with full context — they never have to ask "what happened?"

---

## Phase 8 — Voice State Machine & ThinkingPanel

**What was built:**
- `backend/prism_state.py` — `PrismState` enum (10 states) + `derive_voice_state(case)` as single source of truth
- `frontend/src/config/prismState.js` — JavaScript mirror of the same enum with UI metadata
- `GET /state/{channel}` — lightweight realtime state polling endpoint
- `GET /active-state` — follows the most recently active channel (voice or text), so the dashboard doesn't need to know the channel name
- `ThinkingPanel.jsx` — pipeline progress display, confidence breakdown, tool result card, current action
- `VoiceInterface.jsx` — voiceState transitions driven by real backend response data (UNDERSTANDING → THINKING → [backend phase] → LISTENING)

**Design decision:**
> Every visible AI state corresponds to a real underlying operation. No fake animations. No artificial delays. The content-length-based TTS estimate (`reply.length × 45ms`, clamped 800ms–3000ms) is the only timing heuristic, and it's labeled as such.

**Why:** Per the architecture spec — "Every visible AI state must correspond to a real underlying operation."

---

## Phase 9 — Voice Agent Refactor (Alexa/Siri Quality)

**What was built:**
- `backend/voice_agent.py` (renamed from `pipecat_agent.py`, all misleading "Pipecat" framing removed)
- Full LLM-first conversational architecture: warm, empathetic, fluid responses
- Two-tool schema: `check_transaction` + `escalate_to_human` (proposal only — policy validates)
- `backend/policy.py` — `PolicyDecision` dataclass + `evaluate_escalation()` function

**The deterministic policy gate (PRISM's core differentiator):**
```
LLM proposes escalation (via escalate_to_human tool)
        ↓
evaluate_escalation(case, llm_proposed=True)
        ↓
Calls decide(case) — the same deterministic engine
        ↓
If decide() == ESCALATE → APPROVED
If decide() == anything else → DENIED (CONTINUE), even if LLM proposed it
        ↓
Policy directive injected into follow-up LLM call
("You were going to escalate, but the policy says CONTINUE — help the user instead")
```

**Hard triggers that bypass LLM entirely:** user_requested_human, has_contradiction, tool_failed — these always escalate regardless of what the LLM said.

**Why:** The LLM should speak naturally and fluidly (Alexa/Siri quality). But the LLM should not have unrestricted authority over escalation. `policy.py` enforces this separation — the LLM is a proposer, not a decision-maker.

---

## Phase 10 — Speech Layer Integration (Silero VAD + Faster Whisper + LiteLLM)

**What was built:**
- `backend/llm_service.py` — LiteLLM adapter with primary + fallback provider resilience
- `backend/vad_service.py` — Silero VAD for barge-in detection (WebSocket `/ws/vad`); top-level torch/numpy imports moved into method bodies to avoid import-time crash
- `backend/asr_service.py` — Faster Whisper for Hindi/Hinglish transcription (`POST /asr`, `GET /asr/status`); model lazy-loaded on first use
- Frontend 🎤 mic-to-text button in chat mode (hold to record, release to transcribe via `/asr`)
- LiteLLM fallback: if Groq fails, automatically retries with fallback provider if configured

**Why:**
- LiteLLM: single point of failure on one Groq key is a demo risk. Fallback resilience protects the live demo.
- Silero VAD: proper barge-in detection rather than volume-threshold heuristics.
- Faster Whisper: better Hindi/Hinglish accuracy than Agora's English-first ASR for the text-mode speech input.

---

## Bug Fixes Applied

### Empty assistant messages in dashboard conversation
**Root cause:** The LLM was responding with only the `<EXTRACT>` block and no conversational text. After stripping the block, `clean_content` was empty string `""` and got stored in `conversation_history`.
**Fix:** After `_extract_and_strip`, if `clean_content` is empty, fall back to `_run_deterministic_path(case)` for a guaranteed non-empty reply.

### Agent dashboard conversation showing empty bubbles
**Root cause:** Tool-call assistant messages are stored with `content: null` in conversation_history. The dashboard was rendering these as empty bubble chrome.
**Fix:** Filter `displayMessages` to only messages where `content` is a non-empty string and `role` is `user` or `assistant`.

### UI frozen on "PRISM is thinking..." after LLM error
**Root cause:** The `catch (e) {}` in `sendChatMessage` was silent — LLM failure left `chatSending = true` forever.
**Fix:** Added `setVoiceState('LISTENING')` in the catch block so the UI always recovers.

### `vad_service.py` top-level import crash
**Root cause:** Top-level `import numpy as np` and `import torch` — if torch isn't installed, the entire backend crashed on startup and all endpoints failed.
**Fix:** Moved all torch/numpy imports inside method bodies (lazy imports).

### Conversation history accumulating across sessions
**Root cause:** The `prism-text` channel is reused across sessions. Each new connect appended to the same case's history.
**Fix:** `/session/start` now deletes and recreates the case if the existing one was escalated or taken over. Added `POST /session/reset/{channel}` for manual resets.

### `showEscalation` used without useState declaration in Agent.jsx
**Root cause:** `setShowEscalation` was called in 4 places but `const [showEscalation, setShowEscalation] = useState(false)` was never declared.
**Fix:** Added the missing useState declaration.

### Port 8000 vs 8001 mismatch
**Root cause:** `BACKEND_PUBLIC_URL` defaulted to `http://localhost:8000` but backend runs on 8001. Agora would POST to the wrong port when building the LLM proxy URL.
**Fix:** `main.py` default changed to `http://localhost:8001`. `.env` updated to `8001`.

---

## Architecture Decisions (Final)

### Frontend stack: Vite + React + JavaScript
The PRD originally specified Next.js + TypeScript + Tailwind. The actual implementation uses Vite + React + JSX with inline styles. The PRD has been updated to reflect reality. The reasoning: for a real-time voice hackathon demo, Vite's instant HMR and zero-config setup is faster than Next.js. TypeScript adds value in a team/enterprise context but slows solo hackathon development. The UI is functional, polished, and delivers all required screens.

### LLM + Deterministic gate (not if-else)
The architecture is: LLM proposes (natural language, entity extraction, conversational response) + deterministic policy validates (escalation authority, confidence gating). This is explicitly NOT a chatbot with if-else routing — the LLM drives conversation quality while code owns decisions. See `backend/policy.py` and `backend/decision.py`.

### Agora remains central
Agora's Conversational AI engine handles the real-time voice pipeline (STT + LLM proxy → PRISM → TTS). The browser joins via `agora-rtc-sdk-ng`, publishes mic, and plays back the agent's audio track. This is non-negotiable per the hackathon rules.

### In-memory state (no database)
All case state is in Python dicts. Restaring the backend clears all state. This is intentional for the MVP — PostgreSQL + pgvector are in the future roadmap (Phase 2).

---

## Current State

**All P0 items resolved:**
- `pipecat_agent.py` renamed to `voice_agent.py`, misleading Pipecat framing removed
- `backend/requirements.txt` complete with all dependencies
- `docker-compose.yml` corrected (uses base images, port 8001, no Dockerfile references)
- Render import path handled via `sys.path.insert` in `main.py`
- Port 8000/8001 mismatch fixed in `.env` and `main.py` default

**All P1 items resolved:**
- Frontend stack documented as Vite + React + JavaScript in PRD §29
- Escalation architecture: LLM proposes → deterministic policy validates → ESCALATE or CONTINUE
- API endpoints aligned with PRD §30 contract
- `PrismState` shared between backend (`prism_state.py`) and frontend (`config/prismState.js`)

**All P2 items resolved:**
- Agent dashboard polls `/active-state` (follows voice or text channel dynamically)
- "22 languages" claim replaced with "Hindi, English & Hinglish" throughout
- Dead code removed (`_run_deterministic_path` retained as LLM fallback, not dead)
- `PrismState` enum is the single shared definition

---

## File Map (current)

```
PRISM/
├── sources/
│   ├── prd.md              ← Product Requirements (updated to reflect Vite+React stack)
│   ├── tech-stack.md       ← Technical stack documentation
│   └── history.md          ← This file
│
├── backend/
│   ├── main.py             ← All FastAPI endpoints
│   ├── voice_agent.py      ← Conversational brain (LLM + tools + policy gate)
│   ├── policy.py           ← Deterministic escalation policy gate
│   ├── decision.py         ← Deterministic action decision engine
│   ├── confidence.py       ← Label-based confidence engine
│   ├── context.py          ← CaseState in-memory store
│   ├── tools.py            ← check_transaction mock + escalation ticket
│   ├── prism_state.py      ← PrismState enum + derive_voice_state()
│   ├── llm_service.py      ← LiteLLM adapter with fallback
│   ├── asr_service.py      ← Faster Whisper ASR
│   ├── vad_service.py      ← Silero VAD barge-in
│   └── requirements.txt    ← Complete dependency list
│
├── frontend/src/
│   ├── config/
│   │   ├── languages.js    ← English + Hindi only (Hinglish handled via LLM)
│   │   └── prismState.js   ← PrismState enum mirror (stays in sync with backend)
│   ├── components/
│   │   ├── VoiceInterface.jsx  ← Caller UI (voice + text modes, Agora SDK)
│   │   ├── ThinkingPanel.jsx   ← Live AI state visualization
│   │   ├── EscalationPanel.jsx ← Case card with Take Over
│   │   ├── CasePanel.jsx       ← Case intelligence display
│   │   └── AIActionPanel.jsx   ← Tool call visualization
│   └── pages/
│       ├── Caller.jsx      ← / route
│       └── Agent.jsx       ← /agent route (human dashboard)
│
├── .env                    ← Local secrets (gitignored)
├── .env.example            ← Template for all required vars
├── docker-compose.yml      ← Local dev stack (base images, port 8001)
├── render.yaml             ← Render backend deploy
├── vercel.json             ← Vercel frontend deploy
├── requirements.txt        ← Root requirements (Render installs from here)
└── runtime.txt             ← python-3.11.9
```
