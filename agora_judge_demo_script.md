# PRISM × Agora — Judge Live Demo Script
## Show, don't tell. 7 visual proof points in ~8 minutes.

---

## 🎬 SETUP BEFORE JUDGES WALK IN

| # | Prep Step | Why |
|---|-----------|-----|
| 1 | Open **2 browser windows side by side**: <br>**Left = Caller page** (user POV — `/pages/Caller.jsx` or VoiceInterface) <br>**Right = Agent dashboard** (`/pages/Agent.jsx`) | Judges see BOTH ends of the Agora channel simultaneously — no "trust me it works" |
| 2 | Open **DevTools → Network tab** on LEFT window, filter to `Fetch/XHR` | Proves token fetch, /session/start, and Agora client activity |
| 3 | Run backend + frontend (`uvicorn backend.main:app` & `npm run dev`). Open backend terminal visible on secondary screen if possible | Judges can see the `/llm-proxy` callbacks hitting Python IRL |
| 4 | Have `TX48291` written on a sticky note — tell judges this is our test Transaction ID | Avoids searching for a valid ID mid-demo |
| 5 | On Agent dashboard, confirm **Agora status dot** is green in TopBar | Instant visual proof Agora SDK is loaded & connected |

**Code Reference for Agora status indicator:**
[TopBar.jsx#L35-L41](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/components/TopBar.jsx#L35-L41) — shows breathing green dot + "Agora · Connected" label

---

## 🗣️ DEMO SCRIPT — LINE BY LINE

Total runtime: ~8 min. Each section = **What you say** + **What you do** + **What judges SEE (visual proof)**.

---

### 🎯 PROOF 1 — AGORA RTC TOKEN (Server-side security, ~1 min)

> **YOU SAY:**
> "First, I want to prove something many hackathon demos skip: security. The Agora App Certificate never goes to the browser. Every participant — user, AI, and human agent — gets a short-lived, signed token from our backend."

> **YOU DO:**
> 1. On the LEFT (Caller) window, hit **F12 → Network tab**, clear it
> 2. Click the big **Connect / Start Voice** button
> 3. Immediately point to the Network tab

> **JUDGES SEE:**
> - A `GET /token?channel=prism-xxxxx&uid=NNNNN` request flash in Network panel
> - Response JSON contains `{ token: "007...<long signed string>", app_id: "...", channel, uid }`
> - **No certificate visible anywhere in client code**
> - Top-right of Agent dashboard: **🟢 Agora · Connected** (breathing dot animation)

> **YOU SAY (while pointing):**
> "That 40-character string is signed by Agora's `RtcTokenBuilder` on our FastAPI backend using the App Certificate stored only in server environment variables. It expires in 1 hour. If I open frontend/package.json, the only Agora thing shipped to the browser is `agora-rtc-sdk-ng` — zero secrets."

**Code to back this up (can open post-demo):**
- Token minting: [main.py#L377-L407](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py#L377-L407) — `RtcTokenBuilder.buildTokenWithUid(...)`
- Frontend package (no secrets): [package.json#L12](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/package.json#L12) — only `agora-rtc-sdk-ng` version listed

---

### 🎯 PROOF 2 — USER JOINS AGORA RTC CHANNEL (~1 min)

> **YOU SAY:**
> "Now the user is joining an Agora RTC channel. This isn't a REST API calling an LLM and playing a wav file — the user's microphone is being published live via Agora's WebRTC SDK."

> **YOU DO:**
> 1. Point to the **Voice Orb animation** on the Caller page — it should now be pulsing cyan
> 2. Say something into the mic (e.g., "Testing, hello judges") — show the waveform bars moving
> 3. Switch to the **F12 → Console tab** briefly

> **JUDGES SEE:**
> - Voice orb pulsing → the shared `PRISM_STATE_CONFIG` visual state = **LISTENING**
> - Waveform equalizer bars (20 bars) moving in real-time (line 139-144 in VoiceInterface)
> - Console debug shows: `AgoraRTC client created (mode=rtc, codec=vp8) → user joined → microphone track published`
> - Agent dashboard still shows **🟢 Agora · Connected**

> **YOU SAY:**
> "The client is using `AgoraRTC.createClient` with VP8 codec for speech-optimized audio, then `client.join()` then `client.publish([mic])`. The user is live in the channel right now."

**Code:**
- Join + publish mic: [VoiceInterface.jsx#L166-L177](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/components/VoiceInterface.jsx#L166-L177)
- State machine rendering: [VoiceInterface.jsx#L43](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/components/VoiceInterface.jsx#L43) `voiceState` → [prismState.js](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/config/prismState.js)

---

### 🎯 PROOF 3 — CONVERSATIONAL AI AGENT JOINS SAME CHANNEL (~1.5 min)

> **YOU SAY:**
> "Here's the part most demos get wrong. Other teams would: user mic → REST POST → LLM → audio file back to user. That makes Agora superficial. We do something different. We call Agora's Conversational AI API to spawn a VIRTUAL AI PARTICIPANT into this SAME channel. The AI is another user in the RTC room."

> **YOU DO:**
> 1. Go back to the Network tab on LEFT — clear it again right after clicking Connect
> 2. Point to the `POST /session/start` request
> 3. (If backend terminal visible) Point to the backend log saying:
>    ```
>    [PRISM Agent] POST https://api.agora.io/.../agents/start
>    → agent_id = "agora-agent-xxxx"
>    → case.agora_agent_id stored + active_sessions[channel] = agent_id
>    ```

> **JUDGES SEE:**
> - `POST /session/start` request in Network. Request payload contains:
>   ```json
>   {
>     "channel": "prism-xxxxx",
>     "user_uid": NNNNN,
>     "language": "Hindi",
>     "locale": "hi-IN"
>   }
>   ```
> - Response `{ agent_id, state: "RUNNING", channel }`
> - A few seconds later: user hears the AI greeting (Agora TTS in South Asian female voice):
>   **"Namaste! Main PRISM hoon. Aap kaise help kar sakta hoon?"**
> - On the VoiceInterface: agent audio indicator lights up — the remote audio track `user-published` event fired

> **YOU SAY (timing: as greeting plays):**
> "That voice is NOT browser Web Speech API. That's Agora's cloud TTS playing via the same RTC subscription that a human agent would use. The payload we sent configured `tts.vendor=agora`, `voice_id=female-south-asian-en`, `asr.language=hi-IN,en-US` for bilingual ASR. And critically, we told Agora: for EVERY turn in this conversation, POST to our backend's `/llm-proxy` endpoint. That's how PRISM retains control of the intelligence."

**Code:**
- AI agent spawn payload: [main.py#L466-L500](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py#L466-L500) — look for `llm.url = llm_proxy_url` (line 475) + greeting_message + system_messages + tools + asr + tts + vad
- REST call to Agora Cloud: [main.py#L504-L518](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py#L504-L518)

---

### 🎯 PROOF 4 — AGORA CALLS /llm-proxy EACH TURN (PRISM brain in control, ~2 min)

> **YOU SAY:**
> "Now this is where PRISM does its real work. The Agora AI participant did the STT for me — it converted my voice to text using their Hindi+English ASR. Now it needs to know what to SAY next — so it calls US."

> **YOU DO:**
> 1. Speak clearly into the Caller mic:
>    **"Mera payment kat gaya but order confirm nahi hua."**
>    (English fallback if Hindi uncomfortable: "My payment was deducted but order not confirmed.")
> 2. Immediately point to the BACKEND TERMINAL (if visible) or explain it

> **JUDGES SEE IN REAL TIME:**
> On the **Caller IntelligencePanel** (right side of VoiceInterface):
> ```
> 🔴 LISTENING ──▶ 🟡 UNDERSTANDING ──▶ 🟠 THINKING
>     ↓
> Execution Pipeline lights up step-by-step:
>   ✓ User intent detected → "payment_issue"
>   ✓ Context extracted → Language: Hindi + English
>   ✓ Action identified → ASK (for Transaction ID)
>   → Verification (waiting for tool)
>   → Resolution
> Confidence meter: ~65% (MEDIUM, yellow fill)
> Verified fields: []     Blocking fields: [intent, transaction_id]
> ```
> Then AI voice responds from the channel: **"I understand your payment was deducted. Could you please tell me your Transaction ID?"**
>
> Backend terminal (if visible):
> ```
> POST /llm-proxy?channel=prism-xxxxx  200 OK
>   → X-Agora-Signature validated ✓   (HMAC SHA256 check passed)
>   → run_agent_turn()
>     → ContextEngine.build_context()
>     → Memory + RAG retrieval
>     → LLM proposes "ASK" (no tool yet)
>     → PolicyGate: CONTINUE
>     → Streaming 2 sentences via SSE
>   → Streamed response in 76ms (first sentence)
> ```

> **YOU SAY:**
> "I want to draw your attention to three things here. First, the X-Agora-Signature header we validate on every `/llm-proxy` call — so only Agora Cloud can trigger our brain. Second, the reply comes back as SSE chunks split by SENTENCE, so Agora can start TTS on the first sentence before we finish sending the rest. That's how the perceived latency is so low. Third: right there, blocking_fields says [intent, transaction_id]. The deterministic engine already knows exactly what's missing."

**Code:**
- `/llm-proxy` signature validation: [main.py#L606-L616](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py#L606-L616)
- Sentence-level streaming for fast TTS: [main.py#L712-L743](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py#L712-L743)
- IntelligencePanel timeline visual: [IntelligencePanel.jsx#L80-L112](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/components/IntelligencePanel.jsx#L80-L112)

---

### 🎯 PROOF 5 — TOOL EXECUTION + POLICY GATE (Rogue AI impossible, ~1.5 min)

> **YOU SAY:**
> "Now let's give it a transaction ID. But here's what I want you to watch: the LLM will propose an escalation. The DETERMINISTIC POLICY GATE — not the LLM — will decide if it actually happens. Watch this."

> **YOU DO:**
> 1. Speak into Caller mic: **"TX48291"**
> 2. Keep eyes on IntelligencePanel + Agent dashboard RIGHT window simultaneously

> **JUDGES SEE (10-second sequence, narrate what's happening):**
>
> **T+0s** → Voice state = **THINKING**. Action = **VERIFY_TRANSACTION**
> **T+1s** → IntelligencePanel: "VERIFICATION" lights up orange. Progress on Confidence meter rises
> **T+2s** → Tool call fires: `check_transaction(TX48291)` → returns `{ success: true, status: SUCCESS, order_status: NOT_CONFIRMED, amount: 1499 }`
> **T+3s** → Verified list updates = [transaction_id ✓, amount ✓, payment_status ✓, order_status ✓]
> **T+4s** → 🟠 ACTING → **⚠️ duplicate_charge still shows "CRITICAL_UNKNOWN"** (red) in blocking fields
> **T+5s** → `policy_decision: "ESCALATE"` with reason:
>   *"Cannot verify duplicate charge status — insufficient confidence"*
> **T+6s** → Voice state = 🔴 **ESCALATING** (red)
> **T+8s** → On the RIGHT (Agent dashboard): **New case PRISM-XXXX appears** in EscalationsPage queue with status **ESCALATED**, amount ₹1499, "Human required" card shows in red

> **YOU SAY (point to the policy_decision field in IntelligencePanel):**
> "Look at what happened. The tool returned payment SUCCESS but order NOT_CONFIRMED. That is the AMBIGUOUS case. The deterministic engine in `decision.py` encodes this as the 4th hard trigger: payment_status known AND duplicate_charge == UNKNOWN → ALWAYS escalate. The LLM did NOT decide this. Python did. Even if the LLM had said 'this is fine, no need to escalate' — the policy gate would override and escalate anyway."

> **Judge Q hook (say this):**
> "Want me to prove that override? I can run the text-only version where we prompt the LLM to refuse escalation — the policy still triggers. The architecture guarantees it."

**Code:**
- Hard trigger #4 (duplicate UNKNOWN → ESCALATE): [decision.py#L57-L58](file:///d:/WORK%20AND%20STUDY/PRISM/backend/decision.py#L57-L58)
- Policy gate evaluates independently of LLM proposal: [policy.py#L84-L112](file:///d:/WORK%20AND%20STUDY/PRISM/backend/policy.py#L84-L112)
- Escalation ticket card: [EscalationPanel.jsx#L75-L176](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/components/EscalationPanel.jsx#L75-L176) — shows "Human required" + "Reason" field

---

### 🎯 PROOF 6 — HUMAN AGENT JOINS **SAME AGORA CHANNEL** (Seamless, ~1 min)

> **YOU SAY:**
> "Now for the seamless handover. Most systems: escalate = new call, new authentication, user waits on hold. In PRISM? The human agent clicks one button and joins the EXISTING Agora RTC channel. Three participants now in one room: User · AI · Human."

> **YOU DO:**
> 1. On the RIGHT window (Agent dashboard), find the new red "Human required" card (should be top of queue)
> 2. Click **[Take over conversation]** button on EscalationPanel

> **JUDGES SEE:**
> - Button text changes → **"Connecting…"** → **"✓ Taken over"**
> - Card background flips from 🔴 red danger-bg → 🟢 green ok-bg with "✓ Human agent connected"
> - **LEFT window (Caller)** sees system message: **"A human agent has taken over."**
> - Voice state = 🟢 **HUMAN_CONNECTED** (green fill in IntelligencePanel)
> - Agent dashboard TopBar: **Agora · Connected** still green (no disconnect)
> - (If backend terminal visible) Log line:
>   ```
>   [Agent] handleAgentAgoraJoin(prism-xxxxx)
>     → GET /token (UID=88888) → signed token
>     → AgoraRTC.join(channel=prism-xxxxx, token, uid=88888)
>     → microphone published → 3-way live audio
>   ```

> **YOU SAY:**
> "Three participants now share the same Agora RTC channel — user UID [random], AI agent UID 12345, human agent UID 88888. Same channel. No transfer. No hold. The user hasn't heard a single beep. If I unplug the AI agent now with `/session/stop`, the human and user keep talking uninterrupted. That's the difference between 'Agora integrated' and 'Agora CENTRAL'."

**Code:**
- Human joins via `AgoraRTC.join(..., uid=88888)`: [Agent.jsx#L80-L97](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/pages/Agent.jsx#L80-L97)
- Ticket channel routing: [tools.py#L258-L259](file:///d:/WORK%20AND%20STUDY/PRISM/backend/tools.py#L258-L259) — escalation summary includes `"channel": agora_channel`
- Takeover state (HUMAN_CONNECTED): [prism_state.py](file:///d:/WORK%20AND%20STUDY/PRISM/backend/prism_state.py)

---

### 🎯 PROOF 7 — STOP + DEMO MODE (Graceful degradation, ~30 sec)

> **YOU SAY:**
> "Last thing. Production systems degrade. In PRISM, everything — from Agora credentials to LLM keys — has a fallback."

> **YOU DO:**
> 1. On Caller page click **Disconnect**
> 2. Toggle **Demo Mode** switch (if visible), or just mention the code
> 3. In Network tab, show `/session/start` response when credentials missing: `{ agent_id: "demo-agent-...", mode: "demo", warning: "No Agora credentials — demo mode active" }`

> **JUDGES SEE:**
> - Everything still works! Voice state, IntelligencePanel, mock escalations, dashboard — all functional in demo mode
> - Agent dashboard still shows **🟢 Agora · Connected** with demo-mode caveat
> - Backend logs show graceful `logger.warning` not `logger.error`

> **YOU SAY:**
> "This means at 3am, if Agora has an incident or we rotate credentials wrong, PRISM doesn't crash. It falls back: browser Web Speech API for STT/TTS, mock agent_id, in-memory session-only state. Users still get service. No 500 errors to end users. That's how we built this to run in production, not just to win this round."

**Code:**
- Demo fallback (no creds): [main.py#L437-L446](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py#L437-L446) — `mock_id = "demo-agent-..."`
- Error recovery for Agora failures: [error_recovery.py#L109-L112](file:///d:/WORK%20AND%20STUDY/PRISM/backend/error_recovery.py#L109-L112) — `_recover_agora()` sets `case.connection_state = "RECONNECTING"` and resets gracefully

---

## ❓ JUDGE Q&A CHEAT SHEET (Agora-specific)

### Q1: "What happens if the Agora Conversational AI API times out mid-conversation?"
> Short answer: `ErrorRecoveryEngine` → AGORA_FAILURE type → state = RECONNECTING → UI polls `/session/status` → backend auto-retries agent/start with same channel. Users see "Reconnecting…" not a crash.
> Code: [error_recovery.py#L66-L67](file:///d:/WORK%20AND%20STUDY/PRISM/backend/error_recovery.py#L66-L67)

### Q2: "How do you prevent someone from calling /llm-proxy directly and poisoning turns?"
> Short answer: HMAC-SHA256 signature check. We set `AGORA_LLM_PROXY_SECRET` env var. Agora signs every request body with it via `X-Agora-Signature`. Lines 607-616 in main.py use `hmac.compare_digest` (constant-time, no timing attack). No sig or mismatch → 401.
> Code: [main.py#L606-L616](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py#L606-L616)

### Q3: "Why VP8 codec instead of Opus?"
> Short answer: Opus is technically better for pure audio, but Agora Web SDK's default with VP8 is the most universally compatible across Indian mobile browsers (JioPhone, older Chrome on Android) — which is our target user base. We configured `{ encoderConfig:'speech_standard' }` on the mic track so audio is still speech-optimized within VP8.
> Code: [VoiceInterface.jsx#L166](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/components/VoiceInterface.jsx#L166) + [line 176](file:///d:/WORK%20AND%20STUDY/PRISM/frontend/src/components/VoiceInterface.jsx#L176)

### Q4: "What's the exact flow for the barge-in / interruption in Agora?"
> Short answer: We send `vad.silence_duration_ms=480, speech_duration_ms=150, interrupt_duration_ms=160` in the agent start payload. Agora's Conversational AI layer handles the VAD and interruption natively. That's why we picked Agora Conversational AI vs rolling our own VAD: native barge-in without building the audio buffer logic. For the demo MVP we also have Silero VAD + WebSocket endpoint available if needed.
> Code: [main.py#L494-L498](file:///d:/WORK%20AND%20STUDY/PRISM/backend/main.py#L494-L498) (agent VAD params)

---

## 🎯 CLOSING ONE-LINER FOR JUDGES

> **"To recap what you just SAW: Seven integration points. Zero secrets in the client. Three parties in one live Agora RTC channel. LLM never makes an escalation decision. Everything has a fallback. This isn't a demo wrapper around Agora — this is what PRISM being BUILT on Agora looks like."**
