# PRISM

### Polyglot Real-time Intelligent Support Mediator

> *"PRISM doesn't just understand what people say. It understands when it has enough information to act — and when it doesn't."*

Built for the **EchoSphere: Agora Conversational AI Hackathon** — Problem Statement PS51: Multilingual Assistance-Line Agent with Human Escalation.

---

## The Problem

Traditional voice support systems fail because they assume users will:
- Speak a single, consistent language
- Follow a structured conversation flow
- Describe their problem clearly
- Repeat themselves when transferred to a human agent

Real callers speak Hindi. Or English. Or both in the same sentence — Hinglish. They switch mid-sentence. They have background noise. They forget their transaction ID. They describe problems in unexpected ways.

Most voice bots respond by misunderstanding, looping, or confidently giving the wrong answer.

**PRISM takes a different approach.**

---

## What PRISM Does

PRISM is a real-time multilingual conversational AI that:

1. **Listens** via Agora's real-time voice infrastructure
2. **Understands** natural Hindi, English, and Hinglish speech
3. **Remembers** structured case state across the conversation
4. **Decides** deterministically what to do next (ask, call a tool, escalate)
5. **Acts** by calling external services to verify information
6. **Knows when it doesn't know enough** — and escalates with full context

The differentiator is not multilingual capability. It's the combination of:
- Structured case state (not just raw chat history)
- Deterministic decision engine (LLM for language, code for logic)
- Honest confidence labels (HIGH / LOW / CRITICAL_UNKNOWN)
- Context-preserving human escalation

---

## Architecture

```
USER (voice / Hinglish)
        │
        ▼
   ┌─────────────┐
   │    AGORA    │  ← real-time voice infrastructure
   │  RTC + STT  │    The AI agent joins as a virtual participant
   │  + TTS      │    STT and TTS run in Agora's cloud
   └──────┬──────┘
          │ POST /llm-proxy (OpenAI format)
          ▼
   ┌─────────────────────────────────────────┐
   │           PRISM BACKEND (FastAPI)        │
   │                                         │
   │  /llm-proxy ← intercepts every LLM call │
   │       │                                 │
   │  ┌────┴────┐    ┌──────────────────┐    │
   │  │   LLM   │    │   Case State     │    │
   │  │(language│    │ (structured,     │    │
   │  │ entity  │    │  in-memory)      │    │
   │  │ extract)│    └────────┬─────────┘    │
   │  └────┬────┘             │              │
   │       └────────┬─────────┘              │
   │                ▼                        │
   │         Decision Engine                 │
   │         (pure Python,                   │
   │          no LLM)                        │
   │                │                        │
   │    ┌───────────┼──────────┐             │
   │    ▼           ▼          ▼             │
   │   ASK        TOOL      ESCALATE         │
   │               │           │             │
   └───────────────┼───────────┼─────────────┘
                   ▼           ▼
            Mock Transaction  Human Agent
                  API            Dashboard
```

### LLM vs Code Boundary

| Concern | Owner |
|---------|-------|
| Understanding speech / intent | LLM |
| Extracting entities (TX ID, amount) | LLM |
| Natural conversational responses | LLM |
| Case state fields | **Code** |
| Confidence labels | **Code** |
| Escalation conditions | **Code** |
| Tool call execution | **Code** |
| Ticket creation | **Code** |

---

## Agora's Role

Agora is the core real-time voice infrastructure of PRISM — not an add-on.

- **Agora RTC** — the caller's microphone and speaker connect through Agora's real-time channel
- **Agora Conversational AI Engine** — an AI agent joins the channel as a virtual participant, handling ASR (speech-to-text) and TTS (text-to-speech) entirely in Agora's cloud
- **LLM Proxy** — Agora calls our backend's `/llm-proxy` for every conversation turn, using the OpenAI-compatible chat completions format. This is where PRISM intercepts, injects case context, handles tool calls, and drives the decision engine.

Without Agora, there is no voice. Agora is what makes PRISM a real-time conversational experience rather than a chatbot.

---

## Features

- **Real-time multilingual voice** — Hindi, English, Hinglish, natural code-switching
- **Structured case state** — every conversation builds a typed case object, not just chat history
- **Deterministic decision engine** — ASK / TOOL_CALL / ESCALATE logic in pure Python
- **Honest confidence labels** — HIGH / LOW / CRITICAL_UNKNOWN per field
- **Tool calling** — mock transaction API with real interception and result injection
- **Multi-condition escalation** — missing info, contradiction, tool failure, low confidence, user request
- **Context-preserving handoff** — human agent receives full structured case, not a blank slate
- **Human agent dashboard** — live polling, confidence breakdown, Take Over button

---

## Confidence Model

PRISM uses label-based confidence, not a probabilistic score:

| Label | Meaning | Display |
|-------|---------|---------|
| `HIGH` | Field present AND verified by tool | ~95% |
| `LOW` | Stated by user, not tool-verified | ~55% |
| `CRITICAL_UNKNOWN` | Required field missing or unresolvable | ~41% |

The display percentage (shown in the dashboard) is derived from these labels — it's a UI representation, not a calibrated probability. PRISM is honest about this.

---

## Escalation Triggers

PRISM escalates when ANY of these conditions are true:

1. **User explicitly asked** for a human
2. **Contradictory information** was detected in the conversation
3. **Tool call failed** — transaction could not be verified
4. **Critical field is UNKNOWN** after all available verification steps
5. **Overall confidence score** below the 0.60 threshold

---

## The Demo Flow

The target demo is approximately 2–3 minutes:

| Time | Event |
|------|-------|
| 0:00 | User connects to PRISM |
| 0:10 | User speaks in Hindi: *"Bhai mera payment ka issue hai"* |
| 0:20 | User switches to Hinglish: *"Paise kat gaye but order confirm nahi hua"* |
| 0:30 | PRISM understands: intent=payment_issue |
| 0:40 | PRISM asks: *"Do you have your transaction ID?"* |
| 0:50 | User gives TX48291 |
| 1:00 | PRISM calls `check_transaction("TX48291")` |
| 1:15 | Tool returns: SUCCESS, ₹1,499, NOT_CONFIRMED |
| 1:30 | PRISM: *"I found your ₹1,499 transaction — payment was successful but the order wasn't confirmed"* |
| 1:45 | `duplicate_charge = UNKNOWN` — blocking field flagged |
| 2:00 | Decision engine: ESCALATE |
| 2:10 | PRISM: *"I'm not confident about whether there was a duplicate charge — I don't want to give you wrong information. Let me connect you with a specialist."* |
| 2:20 | Human dashboard receives full structured case |
| 2:30 | Human agent clicks TAKE OVER |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Real-time voice | Agora Conversational AI + RTC |
| Frontend | React 18 + Vite |
| Backend | Python 3.11 + FastAPI |
| LLM | OpenAI-compatible (gpt-4o-mini or any compatible model) |
| TTS | Microsoft Azure (en-IN-NeerjaNeural) |
| State | In-memory (no database required) |

---

## Project Structure

```
prism/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── VoiceInterface.jsx   ← Agora RTC + mic + agent audio
│   │   │   ├── EscalationPanel.jsx  ← Case card with Take Over
│   │   │   └── CasePanel.jsx
│   │   ├── pages/
│   │   │   ├── Caller.jsx           ← / route
│   │   │   └── Agent.jsx            ← /agent route (dashboard)
│   │   └── App.jsx
│   └── package.json
│
├── backend/
│   ├── main.py        ← All FastAPI endpoints
│   ├── agent.py       ← PRISM system prompt
│   ├── context.py     ← CaseState + in-memory store
│   ├── confidence.py  ← FieldConfidence labels
│   ├── decision.py    ← Deterministic decision engine
│   └── tools.py       ← Tool schemas + mock transaction API
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Agora account (https://console.agora.io) — App ID, Certificate, Customer ID, Customer Secret
- LLM API key (OpenAI or any OpenAI-compatible provider)
- Azure Cognitive Services key (for TTS)
- **ngrok or similar** — Agora needs a public URL to call your `/llm-proxy`

### 1. Clone and configure

```bash
git clone <repo-url>
cd prism
cp .env.example .env
# Edit .env with your credentials
```

### 2. Backend

```bash
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Expose backend (required for Agora to call /llm-proxy)

```bash
# In a separate terminal:
ngrok http 8000

# Copy the https URL (e.g. https://abc123.ngrok.io)
# Set in .env: BACKEND_PUBLIC_URL=https://abc123.ngrok.io
# Restart uvicorn after updating .env
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### 5. Open two browser windows

- `http://localhost:5173` — Caller (click mic to connect)
- `http://localhost:5173/agent` — Human Agent Dashboard

---

## Environment Variables

See `.env.example` for all variables. Key ones:

| Variable | Description |
|----------|-------------|
| `AGORA_APP_ID` | Your Agora project App ID |
| `AGORA_APP_CERTIFICATE` | Your Agora App Certificate (for token generation) |
| `AGORA_CUSTOMER_ID` | Agora RESTful API Customer ID |
| `AGORA_CUSTOMER_SECRET` | Agora RESTful API Customer Secret |
| `LLM_API_KEY` | OpenAI or compatible LLM API key |
| `LLM_BASE_URL` | LLM API base URL (default: https://api.openai.com/v1) |
| `LLM_MODEL` | Model name (default: gpt-4o-mini) |
| `AZURE_TTS_KEY` | Azure Cognitive Services key for TTS |
| `AZURE_TTS_REGION` | Azure region (e.g. eastus) |
| `BACKEND_PUBLIC_URL` | Public URL Agora uses to call /llm-proxy (use ngrok locally) |

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/token?channel=&uid=` | Generate Agora RTC token |
| POST | `/session/start` | Start Agora AI agent in channel |
| POST | `/session/stop` | Stop Agora AI agent |
| POST | `/llm-proxy?channel=` | LLM proxy (called by Agora) |
| GET | `/mock/transaction/{id}` | Mock transaction lookup |
| GET | `/cases` | List escalated cases |
| POST | `/cases/{id}/takeover` | Mark case as taken over |
| GET | `/debug/case/{channel}` | Dev: inspect case state |

---

## Future Roadmap

- More Indian languages (Tamil, Telugu, Bengali, Marathi)
- Real payment processor integration
- Persistent storage (PostgreSQL)
- WebSocket-based real-time dashboard updates
- Multi-agent routing
- Conversation analytics
- Sentiment analysis
- CRM integration
- Enterprise multi-tenant deployment

---

## Deployment

### Frontend (Vercel)
- **Framework Preset**: Vite
- **Root Directory**: `frontend` (or repository root with `cd frontend && npm run build`)
- **Build Command**: `npm run build`
- **Output Directory**: `dist` (or `frontend/dist`)
- **Environment Variables**:
  - `VITE_API_URL`: `https://<your-render-backend-url>.onrender.com`

### Backend (Render)
- **Environment**: Python 3.11
- **Root Directory**: `.` (or `backend`)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `PORT`: (Set automatically by Render)
  - `FRONTEND_URL`: `https://<your-vercel-app>.vercel.app`
  - `BACKEND_PUBLIC_URL`: `https://<your-render-backend-url>.onrender.com`
  - `LLM_API_KEY`: Your LLM API key
  - `LLM_BASE_URL`: `https://api.groq.com/openai/v1` (or your provider URL)
  - `LLM_MODEL`: `openai/gpt-oss-20b` (or your model choice)
  - `AGORA_APP_ID`: Your Agora App ID
  - `AGORA_APP_CERTIFICATE`: Your Agora App Certificate
  - `AGORA_CUSTOMER_ID`: Your Agora Customer ID
  - `AGORA_CUSTOMER_SECRET`: Your Agora Customer Secret

### Render Keep-Alive
Render free web services spin down after ~15 minutes of inactivity. To maintain instant responsiveness during hackathon/demo evaluation:

1. **Lightweight Health Endpoint**:
   - `GET /health` returns `{"status":"ok","service":"prism-backend"}` without calling LLM or Agora APIs.
2. **External Scheduler Setup**:
   - Configure an uptime monitor (e.g. [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org)) to perform an HTTP `GET` request every 5 minutes.
   - Target URL: `https://<your-render-backend-url>.onrender.com/health`
   - Interval: `Every 5 minutes`

---

## Hackathon

**Event:** EchoSphere: Agora Conversational AI Hackathon  
**Problem Statement:** PS51 — Multilingual Assistance-Line Agent with Human Escalation  
**Team:** PRISM

