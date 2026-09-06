# PRISM — Technical Approach Presentation Script
## For Judges / Jury Panel

---

## 🎤 PRESENTATION FLOW (Recommended: 7-10 minutes)

| Section | Duration | Slide Focus |
|---------|----------|-------------|
| 1. Opening Hook | 45 sec | The "Why" — what's broken in customer support AI |
| 2. Architecture Overview | 90 sec | The 7-Engine Canonical Pipeline |
| 3. Core Innovation #1 — Intelligence + Policy Separation | 90 sec | LLM Proposes → Policy Approves (no rogue AI) |
| 4. Core Innovation #2 — Memory & Knowledge System | 90 sec | Short-term + Long-term Memory + Semantic RAG |
| 5. Core Innovation #3 — Graceful Degradation & Reliability | 60 sec | Fallback mechanisms, no single point of failure |
| 6. Tech Stack & Engineering Decisions | 60 sec | Why we chose what we chose |
| 7. Live Demo Teaser / Closing | 45 sec | Quick capability showcase + impact statement |

---

## 📝 SECTION-BY-SECTION SCRIPT

---

### 【1】OPENING HOOK (45 seconds)

**[SLIDE: Stark statistic or problem statement visual]**

> **"Imagine this: You're on a customer support call. Money's been deducted from your account, but the order never went through. You're frustrated. The AI voice assistant on the other end keeps saying 'I understand' but does nothing. It can't look up your transaction. It can't tell you if it's a duplicate charge. And worst of all, it can't even escalate you to a human properly. This is the state of AI customer support today."**
>
> **"This is why we built PRISM. PRISM doesn't just TALK like it understands — it ACTS. It verifies. It decides. It escalates correctly. And when embeddings fail, or the LLM hallucinates, the system doesn't break — it degrades gracefully. Today, I'm going to walk you through HOW we engineered this."**

---

### 【2】ARCHITECTURE OVERVIEW (90 seconds)

**[SLIDE: The canonical 7-layer pipeline diagram — USER → INPUT → VOICE → INTELLIGENCE → POLICY → ACTION → VERIFICATION → OUTPUT → USER]**

> **"PRISM is built around a 7-layer canonical pipeline. Every single user interaction flows through this exact same path. No shortcuts. No ad-hoc decisions."**
>
> **"Let me walk you through it: First, the INPUT LAYER captures voice or text. Then the VOICE ENGINE — that's VAD, turn detection, STT using Faster-Whisper, language detection. Here, Agora is our realtime communication fabric connecting users, AI, and humans."**
>
> **"Next is the INTELLIGENCE ENGINE — this is where the LLM lives. But here's the critical design decision: the LLM does NOT make decisions. It PROPOSES actions."**
>
> **"The POLICY ENGINE receives that proposal and validates it against deterministic rules. No exceptions. This is our guardrail against LLM hallucinations."**
>
> **"If approved, the ACTION ENGINE runs the tool — checks transactions, creates tickets. Then VERIFICATION ensures the result is consistent. Finally, the OUTPUT LAYER generates a TTS response and streams it back to the user."**
>
> **"This separation — between understanding and deciding — is the single most important engineering decision in PRISM."**

**Code Reference:**
- Pipeline orchestrated in [voice_agent.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/voice_agent.py)
- State machine in [PRISM_V-1-FINAL.md](file:///d:/WORK%20AND%20STUDY/PRISM/PRISM_V-1-FINAL.md#L11-L68)

---

### 【3】CORE INNOVATION #1 — INTELLIGENCE + POLICY SEPARATION (90 seconds)

**[SLIDE: Two-column visual — LEFT: "LLM proposes" bubble showing tool calls, RIGHT: "Deterministic Policy Gate" with checkmarks/X's]**

> **"Let me zoom in on what makes PRISM different from every other AI support agent out there. In a typical system, the LLM has full authority — it can escalate, it can make up facts, it can do whatever the prompt says. And that's dangerous."**
>
> **"In PRISM, the LLM is the creative intelligence. It understands the user, extracts entities, proposes actions like 'escalate_to_human' or 'check_transaction'. But that proposal stops here."**
>
> **"Next, it hits the DETERMINISTIC POLICY GATE — pure Python, no LLM, completely auditable. The policy engine re-evaluates every decision using verified case facts, confidence scores, and hard-coded escalation triggers."**
>
> **"There are only four ways to escalate in PRISM: The user explicitly asked for a human. Contradictory information was detected. The verification tool failed. Or we have SUCCESS payment but NOT_CONFIRMED order — that ambiguous 'money taken, order not there' case. That's it."**
>
> **"If the LLM proposes escalation but none of these four triggers are met? The policy OVERRIDES it. The AI keeps helping. Conversely, even if the LLM FORGETS to propose escalation but a trigger fires? The policy escalates anyway. The LLM cannot suppress a necessary escalation."**
>
> **"This is how you build trustworthy AI. Intelligence without authority."**

**Code References:**
- Policy gate: [policy.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/policy.py#L68-L139) `evaluate_escalation()`
- Deterministic decision engine: [decision.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/decision.py#L22-L65) `decide()`
- Escalation triggers: lines 36-58 in `decision.py`

---

### 【4】CORE INNOVATION #2 — MEMORY & KNOWLEDGE SYSTEM (90 seconds)

**[SLIDE: Three-layer memory pyramid — BOTTOM: Knowledge Base (semantic), MIDDLE: Long-term Memory (consent-gated DB), TOP: Short-term Memory (session)]**

> **"Next, let me show you how PRISM remembers things — and crucially, how it FORGETS on demand."**
>
> **"We have a three-tier memory architecture."**
>
> **"Tier 1: Short-term Memory. Lives on the CaseState object. Session-scoped. Top 8 most recent entries go into the LLM context. Dies when the session ends. No persistence, no privacy risk."**
>
> **"Tier 2: Long-term Memory. This is the interesting one. It's SQLite-backed, but ONLY activates if the user explicitly OPTS IN to memory consent. Consent is OFF by default. If the user revokes consent, we IMMEDIATELY delete every single persisted memory for that channel — within the same request cycle."**
>
> **"And Tier 3: The Knowledge Base. This is our RAG system. We ingest documents — refund policies, FAQs, payment policies — chunk them 500 tokens with 50 overlap, embed them using the multilingual MiniLM model, store in SQLite, and run cosine similarity search. Top 3 chunks go to the LLM context with source citations."**
>
> **"And the best part? Every memory retrieval and knowledge search result is tracked in the case object and exposed to the frontend. The agent dashboard can see exactly what the AI saw. No black box."**

**Code References:**
- Unified Memory Manager: [memory_manager.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/memory_manager.py#L32-L233)
  - Short-term: `remember()` line 45, Long-term: `remember_long_term()` line 99
  - Context assembly: `get_relevant_context()` line 158 (top-8 short + top-3 long)
  - Consent gating: line 107 `if not getattr(case, "memory_consent", False)`
  - Data wipe: `forget_all_long_term()` line 142
- Knowledge Base + RAG: [knowledge_base.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/knowledge_base.py)
  - Chunking: `chunk_text()` line 130, 500 tokens / 50 overlap
  - Embedding model: `paraphrase-multilingual-MiniLM-L12-v2` (line 34) — multilingual!
  - Semantic search: `semantic_search()` line 423, cosine similarity line 184
- Context assembly order: [context_engine.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/context_engine.py#L34-L99) `build_context()`

---

### 【5】CORE INNOVATION #3 — GRACEFUL DEGRADATION & RELIABILITY (60 seconds)

**[SLIDE: Fallback chain visual — Embedding ON → Embedding OFF → Keyword Search. System works at every level.]**

> **"Any production system needs to handle failure. PRISM doesn't just handle failure — it was designed for it from day one."**
>
> **"Take the Knowledge Base: If sentence-transformers or PyTorch isn't available? No problem. The EmbeddingProvider class detects this instantly and falls back. The system switches from semantic cosine similarity search to keyword-overlap scoring. The RAG still works. Responses might be slightly less accurate, but the system never goes down."**
>
> **"Long-term memory: If SQLite isn't available or the table fails to create? The MemoryManager detects it and LongTermMemory simply returns None. Short-term memory still works. Context assembly never breaks."**
>
> **"Memory context, RAG retrieval, tool schemas — every optional component is wrapped in try/catch and logged as a warning, not an error. Failures are isolated. They never cascade."**
>
> **"This is how you build an AI system for production environments. Not one that works 95% of the time, but one that works 100% of the time — at varying levels of intelligence."**

**Code References:**
- Embedding graceful fallback: [knowledge_base.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/knowledge_base.py#L59-L118) `EmbeddingProvider`
  - Lazy load with try/except line 77-90
  - Keyword fallback: `_keyword_score()` line 204, `keyword_search()` line 463
- LTM graceful disable: [memory_manager.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/memory_manager.py#L86-L97) `_get_ltm()` — returns None on failure
- Context engine failure isolation: [context_engine.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/context_engine.py#L68-L81) try/except memory retrieval

---

### 【6】TECH STACK & ENGINEERING DECISIONS (60 seconds)

**[SLIDE: Tech stack table — FastAPI + Python + Agora + LiteLLM + SQLite + React + Vite]**

> **"Now let me quickly walk through the stack and why each piece was chosen."**
>
> **"Backend: FastAPI + Python 3.11. Python because the AI ecosystem is unmatched. FastAPI for async-native performance and Pydantic validation. Every API request is validated with Pydantic models."**
>
> **"Realtime: Agora. This is non-negotiable. PRISM is a REALTIME system first, an AI application second. Agora is the communication fabric that connects the user, the AI participant, and the human agent in the same audio channel. Human takeover is seamless — the human joins the existing Agora session, no new call, no re-authentication."**
>
> **"LLM: LiteLLM with Groq's GPT-OSS-20B as default. Why LiteLLM? Provider abstraction. If we need to switch to GPT-4, Claude, Gemini, or an open-source model tomorrow — zero code changes, one config update."**
>
> **"Storage: SQLite for MVP, PostgreSQL for production. Why SQLite? Zero-config, file-based, perfect for a hackathon MVP. The schema is production-ready, so migration to Postgres is a one-line change."**
>
> **"Frontend: Vite + React. No TypeScript, no CSS framework — keeps the build lean and iteration fast for MVP."**
>
> **"Deployment: Render backend + Vercel frontend + Agora Cloud. CDN-delivered frontend, globally distributed realtime."**

**Code References:**
- Tech stack docs: [tech-stack.md](file:///d:/WORK%20AND%20STUDY/PRISM/sources/tech-stack.md)
- LLM abstraction (LiteLLM): [llm_service.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/llm_service.py)
- Database abstraction: [database.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/database.py)
- Agora token generation + session API: [main.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py)

---

### 【7】LIVE DEMO TEASER / CLOSING (45 seconds)

**[SLIDE: Impact metrics or demo screenshot — Agent dashboard showing case with citations, policy decision, escalation status]**

> **"To wrap this up: PRISM solves three fundamental problems that current AI customer support gets wrong."**
>
> **"One: NO HALLUCINATED ESCALATIONS. The deterministic policy gate ensures the LLM can neither escalate a good case nor suppress a bad one. Every escalation decision is auditable, reproducible, and encoded in pure Python."**
>
> **"Two: PRIVACY-FIRST MEMORY. Consent is opt-in, not opt-out. Revoke consent, data is wiped in the same request. No lingering data. No shadow profiles."**
>
> **"Three: BULLETPROOF RELIABILITY. Embeddings fail → keyword search works. Database unavailable → session memory still runs. Optional components never break the core pipeline."**
>
> **"PRISM isn't just another chatbot with a voice interface. It's a realtime, verified, policy-governed support mediator. The AI understands. The policy decides. The tools act. The humans are there when it matters. Thank you — and now let me show you it working live."**

---

## 🎯 JUDGE Q&A PREP — ANTICIPATED QUESTIONS

### Q: "What happens if the LLM itself is hallucinating or under a prompt injection attack?"
> **"Great question. This is exactly why the policy layer exists. The LLM can output anything it wants in the tool call — but the policy gate re-evaluates the decision independently using only VERIFIED facts (things written to CaseState.verified by actual tool calls). The LLM's output is never a source of truth for escalation. Verified case facts are. Additionally, tool calls go through input validation, authorization checks, and parameter validation in tools.py before any external system is touched."**
> Reference: [policy.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/policy.py#L68-L139) `evaluate_escalation()` re-runs `decide(case)` independent of LLM proposal.

### Q: "How scalable is this architecture? What if you have 10,000 concurrent calls?"
> **"Excellent question. The current MVP uses SQLite and Render for simplicity, but the architecture was designed with horizontal scaling in mind. There's a clear path: (1) Move the persistent layer from SQLite to PostgreSQL. Same schema, SQLModel-compatible, zero code changes to business logic. (2) Move session-scoped state from in-memory dict to Redis — already designed in the tech stack. (3) Put a load balancer in front of FastAPI nodes. The stateless policy engine + decision engine means any node can handle any request. Agora handles all realtime infrastructure. We documented this evolution path in the tech stack spec."**
> Reference: [tech-stack.md](file:///d:/WORK%20AND%20STUDY/PRISM/sources/tech-stack.md#L1549-L1610) "Architecture Evolution" section.

### Q: "Why multilingual embeddings? How does that affect accuracy vs English-only models?"
> **"We specifically chose `paraphrase-multilingual-MiniLM-L12-v2` because PRISM targets Indian users, who commonly switch between English, Hindi, and Hinglish mid-conversation. This model was trained on 50+ languages and produces aligned embeddings — meaning the query 'refund kitne din me aayega' (Hindi) and 'when will I get my refund' (English) land in the same embedding space. The tradeoff is a slight accuracy drop on pure English benchmarks compared to English-only models like all-MiniLM. But for multilingual code-switching scenarios, which are the reality of our user base, the multilingual model is dramatically more effective. And if accuracy is ever insufficient, because we use LiteLLM-style embedding abstraction, we can swap the model in one line of config."**
> Reference: [knowledge_base.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/knowledge_base.py#L34) `EMBEDDING_MODEL = ...`

### Q: "How do you handle consent revocation? What if the request times out?"
> **"Consent revocation is a first-class operation. When the user toggles memory_consent from True to False, main.py calls `memory_manager.forget_all_long_term(case)` which executes `DELETE FROM memories WHERE channel = :channel` in a single synchronous transaction. This happens BEFORE the consent flag is persisted — so if the DELETE fails, consent isn't actually revoked. We return a 500 and the flag stays True. Atomic semantics: revocation and deletion are one operation. Additionally, all memories have optional TTL via expires_at, and a prune_expired() method runs periodically."**
> Reference: [memory_store.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/memory_store.py#L172-L194) `delete_all()` returns deleted count.

### Q: "What about citation accuracy? How do you prevent the LLM from making up policy facts?"
> **"Great question. Two mechanisms: First, the RAG context is injected as a SYSTEM message labeled 'RELEVANT KNOWLEDGE BASE' with an explicit source field per chunk. The LLM system prompt instructs it to cite sources when referencing policy. Second, we track rag_citations on the CaseState object — every retrieved chunk has its source stored in the case. The frontend IntelligencePanel shows exactly which documents the AI retrieved for that turn. The agent dashboard can cross-reference the AI's response against the actual retrieved chunks. No invisible context."**
> Reference: [context_engine.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/context_engine.py#L84-L89) retrieved_knowledge injected with max 2 chunks.

---

## ⚡ DELIVERY TIPS

1. **Energy matters**: Lean slightly forward when explaining the policy gate — this is your "wow" moment.
2. **Use hand gestures** to physically separate "LLM proposes" (left hand) from "Policy approves" (right hand) — judges will remember the visual separation.
3. **Don't read the slides**. The slides are visual anchors. Use the script as talking points, not a teleprompter.
4. **Emphasize contrast**: "Every other AI gives the LLM the keys. We built a separate lockbox."
5. **Pause after innovations**: After explaining each core innovation, pause 2 seconds. Let it land.
6. **If running short**: Cut section 6 (tech stack) to 30 seconds, focus on innovations 1 and 2.

---

## 🔗 FILE REFERENCE CHEAT SHEET (for quick navigation during judging)

| Component | File | Key Lines |
|-----------|------|-----------|
| Policy Gate | [policy.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/policy.py) | 68-139 |
| Decision Triggers | [decision.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/decision.py) | 22-65 |
| Memory Manager | [memory_manager.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/memory_manager.py) | 32-233 |
| Long-term Memory DB | [memory_store.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/memory_store.py) | 26-288 |
| Knowledge Base + RAG | [knowledge_base.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/knowledge_base.py) | 221-567 |
| Context Assembly | [context_engine.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/context_engine.py) | 22-142 |
| Voice Agent Pipeline | [voice_agent.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/voice_agent.py) | 1-200 |
| Tech Stack Full Doc | [tech-stack.md](file:///d:/WORK%20AND%20STUDY/PRISM/sources/tech-stack.md) | 1-1692 |
| Architecture Roadmap | [PRISM_V-1-FINAL.md](file:///d:/WORK%20AND%20STUDY/PRISM/PRISM_V-1-FINAL.md) | 1-150 |
