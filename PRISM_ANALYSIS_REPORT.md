# PRISM — Project Analysis Report

**Date:** 2026-09-05
**Scope:** Current folder structure · what works · what is out of date / not aligned with the PRD · tech-stack conformance
**Ground truth:** `sources/prd.md` (PRD v1.0) and `sources/tech-stack.md`

---

## 1. Executive Summary

**The MVP is functionally complete.** The full PRISM support loop exists end-to-end — voice + text intake, LLM understanding, `check_transaction` tool calling, confidence/verification, escalation, an agent dashboard, and human takeover over Agora. Against the PRD's 17 functional requirements, ~13 are fully met and ~4 are partial.

**The gaps are architectural and cosmetic, not functional:**

1. **Frontend stack is a wholesale substitution.** The PRD and tech-stack *mandate* Next.js + TypeScript + Tailwind + shadcn/ui + Framer Motion + Zustand. The actual app is **Vite + React (plain JavaScript) with inline styles** and none of the mandated libraries. This is the single largest deviation from spec.
2. **A "decision layer vs LLM" contradiction.** The README/PRD promise that a *deterministic* layer controls escalation and "the LLM does not control decisions." In the live code, the **LLM controls escalation** (via an `escalate_to_human` tool); the deterministic `decision.py` no longer drives the conversation.
3. **Misleading "Pipecat" framing + dead/duplicate code.** `pipecat_agent.py` claims to be "Powered by Pipecat" but Pipecat is not installed, the referenced `1Z/` directory doesn't exist, and the code is plain LiteLLM tool-calling. There are also two competing system prompts and unreachable dead code.
4. **API endpoint names drift from spec**, and **`docker-compose.yml` is broken** (references Dockerfiles that don't exist).

None of these block a demo; all of them matter if this is graded against the PRD/tech-stack or handed to another engineer.

---

## 2. Current Folder Structure (annotated)

```
PRISM/
├── sources/                     ← ground-truth specs (untracked in git)
│   ├── prd.md                   ← PRD v1.0
│   └── tech-stack.md            ← Technical stack spec
│
├── backend/                     ← FastAPI (Python)
│   ├── main.py            (895) ← all endpoints; MODIFIED, contains dead code
│   ├── pipecat_agent.py   (259) ← NEW/untracked; live conversation brain (LiteLLM, NOT Pipecat)
│   ├── agent.py           (legacy) ← old <EXTRACT> prompt; dead in live path
│   ├── decision.py        ← deterministic engine; now only feeds UI state
│   ├── confidence.py      ← label-based confidence (HIGH/LOW/CRITICAL_UNKNOWN)
│   ├── context.py         ← in-memory CaseState (dicts; no DB)
│   ├── tools.py           ← MOCK_TRANSACTIONS + check_transaction + escalation ticket
│   ├── llm_service.py     ← LiteLLM adapter (Groq default) with fallback
│   ├── asr_service.py     ← Faster Whisper (server-side ASR)
│   ├── vad_service.py     ← Silero VAD (barge-in)
│   ├── test_integration.py, test_pipecat_agent.py  ← pytest
│   └── requirements.txt   ← MISSING litellm/whisper/vad/torch (see §6)
│
├── frontend/                    ← Vite + React (JavaScript, NOT Next.js/TS)
│   └── src/
│       ├── App.jsx / main.jsx / index.css
│       ├── pages/        Caller.jsx, Agent.jsx (1142-line dashboard)
│       ├── components/   VoiceInterface, CasePanel, EscalationPanel,
│       │                 ThinkingPanel, AIActionPanel
│       ├── config/languages.js  ← only en + hi defined
│       └── lib/          api.js, tts.js (browser SpeechSynthesis), languages.js
│
├── README.md              ← honest about actual stack (React/Vite/JS)
├── docker-compose.yml     ← BROKEN: references non-existent Dockerfiles
├── render.yaml            ← backend deploy (uvicorn backend.main:app)
├── vercel.json            ← frontend deploy
├── requirements.txt       ← root copy (full deps)
├── runtime.txt            ← python-3.11.9
├── .env / .env.example    ← secrets server-side (good)
└── 1Z/                    ← REFERENCED by pipecat_agent.py but DOES NOT EXIST
```

Observations:
- `sources/`, `backend/pipecat_agent.py`, and `backend/test_pipecat_agent.py` are **untracked** (per git status) — the current "live brain" isn't committed yet.
- The structure is a **flat two-app layout**, not the tech-stack's recommended monorepo (`apps/web`, `apps/backend`, `packages/`). That's acceptable for a hackathon MVP but differs from tech-stack §49.

---

## 3. What's Working (implemented & functional)

| Area | Status | Notes |
|---|---|---|
| Closed-loop MVP | ✅ | Voice + text → understand → tool → confidence → escalate → dashboard → takeover, all present |
| Agora as central fabric | ✅ | `/session/start` launches an Agora **Conversational AI v2** agent; server-side token generation; human agent joins the same channel for takeover. This satisfies the tech-stack's "critical engineering rule" — Agora is **not** a superficial mic API (assuming creds are configured). |
| Server-side secret architecture | ✅ | App Certificate / LLM keys stay on the backend; browser only gets App ID + temp token. Matches PRD §16 security & tech-stack §31. |
| Pluggable LLM | ✅ | LiteLLM adapter, Groq `openai/gpt-oss-20b` default, primary→fallback resilience. Matches tech-stack §20 "model-agnostic." |
| Tool calling + verification | ✅ | `check_transaction` invoked by the LLM; results verified before claims; `escalate_to_human` on uncertainty. |
| Confidence engine | ✅ (adapted) | Label-based (HIGH/LOW/CRITICAL_UNKNOWN → display %). Works, but see §5 for the numeric-confidence gap. |
| Agent dashboard + takeover | ✅ | Rich 3-column dashboard (`Agent.jsx`); `/cases/{id}/takeover`; Agora join at AGENT_UID. Matches PRD §19–21. |
| Text fallback | ✅ | Chat mode uses the same intelligence layer via `/chat`. Matches PRD §22 / FR-17. |
| Graceful fallbacks | ✅ | Demo mode, `_generate_human_fallback_reply`, and frontend error-text detection prevent raw "LLM Error"/tracebacks reaching users. Matches PRD §32 & README reliability. |
| Voice greeting + TTS race fix | ✅ | `tts.js` pre-warms `getVoices()` to avoid Chrome/Edge empty-voice race. Nice touch. |

**PRD Functional Requirements scorecard:**

| FR | Requirement | Status |
|---|---|---|
| FR-01 | Voice session start/stop | ✅ |
| FR-02 | Agora channel | ✅ |
| FR-03 | AI participant | ✅ (Agora ConvAI v2) |
| FR-04 | Speech recognition | ✅ (Agora STT + Faster Whisper `/asr`) |
| FR-05 | Partial/live transcript | ⚠️ Only in demo mode — real voice transcripts aren't surfaced to the UI |
| FR-06 | Hindi/English/Hinglish | ✅ understanding · ⚠️ only en+hi in config (see §5) |
| FR-07 | Structured context | ✅ (in-memory) |
| FR-08 | Intent detection | ✅ |
| FR-09 | Missing-info / next-best-question | ⚠️ now LLM-driven, not the deterministic engine |
| FR-10 | Tool calling | ✅ |
| FR-11 | Verification before resolution | ✅ |
| FR-12 | Confidence | ⚠️ label-based, not numeric as PRD examples show |
| FR-13 | Escalation | ✅ |
| FR-14 | Case creation w/ context | ✅ |
| FR-15 | Agent dashboard | ✅ |
| FR-16 | Human takeover | ✅ |
| FR-17 | Text fallback | ✅ |

---

## 4. Tech-Stack Conformance

| Layer | Spec (tech-stack.md) | Actual | Verdict |
|---|---|---|---|
| Web framework | **Next.js (App Router)** | Vite + React SPA | ❌ Deviates |
| Language | **TypeScript** | JavaScript (.jsx) | ❌ Deviates |
| Styling | **Tailwind CSS** | Inline styles + `index.css` vars | ❌ Deviates |
| Components | **shadcn/ui** | Hand-rolled | ❌ Deviates |
| Animation | **Framer Motion** | CSS + `requestAnimationFrame` | ❌ Deviates |
| State | React hooks → **Zustand** | React hooks only | ⚠️ Partial (Zustand not required for MVP) |
| Realtime | **Agora RTC + ConvAI + STT + TTS** | Agora RTC + ConvAI v2 | ✅ |
| Backend | **FastAPI** | FastAPI | ✅ |
| Backend lang | **Python** | Python 3.11 | ✅ |
| Validation | **Pydantic** | Pydantic (v2) | ✅ |
| LLM | **Pluggable adapter** | LiteLLM | ✅ |
| DB | PostgreSQL *(Optional/MVP)* | In-memory dicts | ✅ allowed for MVP |
| Cache | Redis *(Optional/MVP)* | None | ✅ allowed for MVP |
| Deploy FE | **Vercel** | `vercel.json` present | ✅ |
| Deploy BE | **Render** | `render.yaml` present | ✅ |
| Monitoring | Sentry *(optional)* | None | ⚠️ optional |
| Testing | Pytest / Playwright / Vitest | Pytest only (backend) | ⚠️ partial |

**Bottom line:** the **backend + realtime + deployment layers conform well**; the **entire mandated frontend stack does not.** The README's own "Technology Stack" section has been rewritten to match reality (React/Vite/JS) — so the README is honest, but it now *contradicts* `prd.md §29` and `tech-stack.md §50/§52`, which still list Next.js/TS/Tailwind as **required**.

---

## 5. Not Aligned / Out of Date vs the PRD

### 5.1 Frontend framework (largest deviation)
PRD §29 and tech-stack §3–9, §50, §52, §54 require Next.js + TypeScript + Tailwind + shadcn/ui + Framer Motion. The implementation uses **none** of these. Functionally the UI delivers the required screens, but it is a different stack than the documents call for. **Decision needed:** update the specs to bless Vite+React, or migrate the frontend.

### 5.2 "Deterministic decision layer" is no longer in control
- README explicitly differentiates PRISM from traditional AI: *"LLM often controls decisions"* (traditional) vs *"Deterministic decision layer"* (PRISM). PRD §5 principle 4 and §17 echo this.
- **Reality:** the live path (`pipecat_agent.run_pipecat_agent_turn`) lets the **LLM decide escalation** via the `escalate_to_human` tool. `decision.py` (the deterministic engine) is now used **only to derive UI state**, not to gate escalation.
- This is a meaningful architectural drift from the product's headline differentiator. Either re-assert deterministic gating around the LLM's escalation, or update the narrative.

### 5.3 Confidence is label-based, not numeric
PRD §17 and the demo script show numeric confidence (e.g., "AI confidence: 61%", "Resolution confidence: 54%"). `confidence.py` uses fixed labels (HIGH=0.95 / LOW=0.55 / CRITICAL_UNKNOWN=0.41) mapped to a display score. It's a reasonable MVP proxy but isn't the per-decision confidence the PRD describes.

### 5.4 Live transcript only in demo mode (FR-05 / PRD §11)
In real voice mode, `VoiceInterface.jsx` never populates the `messages` array from Agora ConvAI transcripts — the live transcript panel only animates in **demo mode**. PRD §11 wants partial transcription displayed during real speech.

### 5.5 "22 Eighth Schedule languages" overclaim
`README` and the UI advertise "22 Eighth Schedule Indian languages + English," but `frontend/src/config/languages.js` defines only **`en` and `hi`**. The PRD only requires Hindi/English/Hinglish, so this is *functionally fine* — but the 22-language claim is unsupported by the code.

### 5.6 API endpoint naming drift
| Spec | Actual |
|---|---|
| `POST /tools/check-transaction` (PRD §30) | `GET /mock/transaction/{tx_id}` (tool runs internally via LLM tool-call) |
| `POST /escalation/create` (tech-stack §34) | `GET /cases` + internal ticket creation |
| `GET /escalation/{case_id}` | `GET /cases/{case_id}` |
| `POST /escalation/{case_id}/takeover` | `POST /cases/{case_id}/takeover` |
| `GET /session/{session_id}` (PRD §30 / tech-stack §34) | **Missing** |
| `GET /conversation/{session_id}` (tech-stack §34) | **Missing** |

Functionally equivalent, but any test/consumer written to the documented contract will break.

### 5.7 State machine is ad-hoc, not a shared enum
PRD §12 and tech-stack §27 specify a formal `PrismState` enum (10 states) shared with the frontend. The backend derives states as ad-hoc strings in `/state/{channel}` and `_build_ai_state`, and the frontend tracks a subset (`IDLE, CONNECTING, LISTENING, UNDERSTANDING, THINKING, SPEAKING, ESCALATING`) — `ACTING/CHECKING/HUMAN_CONNECTED` aren't consistently represented. No single shared enum exists.

---

## 6. Bugs, Dead Code & Config Issues

1. **`pipecat_agent.py` is not Pipecat.** Header says *"Powered by Pipecat framework (cloned under ./1Z)"* but: `1Z/` doesn't exist, `pipecat` is not in either `requirements.txt`, so `PIPECAT_AVAILABLE` is `False`, and the code uses plain LiteLLM tool-calling. **Fix the comment/naming** to avoid misleading reviewers (the logic itself is fine). Neither the PRD nor tech-stack mention Pipecat — it's an unplanned addition.

2. **Two competing system prompts.** `agent.py`'s `<EXTRACT>{json}</EXTRACT>` prompt is still passed to Agora in `/session/start`, but the live `/llm-proxy` and `/chat` paths use `pipecat_agent.py`'s Siri/Alexa prompt + tool-calling. The EXTRACT mechanism is effectively **dead in the live path**. Pick one.

3. **Dead code:** `_run_deterministic_path()` in `main.py` is defined but never called.

4. **`docker-compose.yml` is broken.** It builds `./backend/Dockerfile` and `./frontend/Dockerfile` — **neither file exists**. It also sets backend port `8000` and `VITE_API_URL=http://localhost:8000`, conflicting with the Vite dev-proxy default of `8001`. As written, `docker compose up` fails.

5. **Port default inconsistency.** `main.py` runs uvicorn on `PORT` default **8001**, but `BACKEND_PUBLIC_URL` defaults to `http://localhost:8000`. The LLM-proxy URL handed to the Agora agent is built from `BACKEND_PUBLIC_URL`, so with local defaults it points at `:8000` while the server is on `:8001`. Harmless in prod (you set `BACKEND_PUBLIC_URL` explicitly), but a latent local-dev trap. Frontend error strings also hard-code "port 8001".

6. **`backend/requirements.txt` is incomplete.** It lists only fastapi/uvicorn/httpx/dotenv/agora-token-builder/pydantic — **missing** `litellm`, `faster-whisper`, `silero-vad`, `torch`, `numpy`, `websockets` that the code imports. The **root** `requirements.txt` has the full set, and `render.yaml` installs from root — so Render is fine, but anyone installing from `backend/` gets `ImportError`.

7. **Render import-path risk (verify).** `render.yaml` runs `uvicorn backend.main:app` from repo root, but backend modules import as top-level (`from context import ...`, `from tools import ...`). If `backend/` isn't on `sys.path`, these imports fail on Render. Worth a deploy smoke-test.

8. **Dashboard channel is hard-coded.** `Agent.jsx` polls `/state/prism-text` (the text channel) every 2s, so during a live **voice** call (channel `prism-demo`) the dashboard's live-state view won't track the voice session.

---

## 7. Prioritized Recommendations

**P0 — correctness / honesty**
- Fix the `pipecat_agent.py` "Powered by Pipecat" comment (it's LiteLLM), or actually vendor Pipecat. Remove the `1Z/` path shim.
- Complete `backend/requirements.txt` (add litellm, faster-whisper, silero-vad, torch, numpy, websockets) so a standalone backend install works.
- Fix or delete `docker-compose.yml` (add the two Dockerfiles, or remove the file). Align its ports with `8001`.
- Smoke-test the Render start command for the `backend.main` import path.

**P1 — spec alignment (decide & document)**
- Resolve the **deterministic-vs-LLM escalation** contradiction: either gate `escalate_to_human` behind `decision.py`, or update the PRD/README narrative to say the LLM decides.
- Reconcile the **frontend-stack decision**: officially amend `prd.md §29` / `tech-stack.md §50` to Vite+React+JS, *or* plan a migration. Right now the docs and code disagree.
- Rename escalation/tools endpoints to the documented contract (`/escalation/*`, `/tools/check-transaction`) or update the docs; add `GET /session/{id}`.

**P2 — polish**
- Wire real Agora ConvAI transcripts into the voice-mode `messages` list (delivers FR-05 live transcript outside demo mode).
- Make the dashboard channel dynamic (voice vs text) instead of hard-coded `prism-text`.
- Remove dead code (`_run_deterministic_path`, the legacy EXTRACT prompt if unused).
- Align the "22 languages" claim with reality, or add the language configs.
- Introduce a shared `PrismState` enum (backend ↔ frontend) per tech-stack §27.

---

## 8. Verdict

PRISM is a **working, demo-ready MVP** that nails the hard parts — real Agora realtime voice with an AI participant, tool-calling with verification, uncertainty-driven escalation, and a context-preserving human handoff. The **backend and realtime architecture are faithful to the spec.**

The work that remains is **reconciliation, not construction**: the frontend was built on a deliberately simpler stack than the documents mandate, the "deterministic decision layer" story no longer matches the LLM-driven code, and a handful of naming/config/dead-code issues make the repo look less finished than it is. Closing the P0/P1 items would bring the implementation and its own documentation back into agreement.
