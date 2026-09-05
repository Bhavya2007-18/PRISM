# PRISM — Technical Stack

> **Polyglot Real-time Intelligent Support Mediator**
>
> Technical architecture, technologies, infrastructure, integrations, and engineering decisions for PRISM.

---

# 1. Architecture Overview

PRISM follows a **Realtime AI + Tool-Calling + Human-Handoff architecture**.

```text
┌──────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                         │
│                                                              │
│        Vite + React SPA       │        Mobile App             │
│        React + JavaScript     │        Future / Phase 2       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                     REALTIME LAYER                           │
│                                                              │
│                         AGORA                                │
│                                                              │
│  RTC │ Conversational AI │ STT │ TTS │ Events │ Data │ Voice │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│                                                              │
│                       FastAPI                                │
│                                                              │
│ Session │ Auth │ LLM Proxy │ Context │ Tools │ Escalation   │
└───────────────┬──────────────┬──────────────┬────────────────┘
                │              │              │
                ▼              ▼              ▼
        ┌────────────┐  ┌────────────┐  ┌──────────────┐
        │ LLM Layer  │  │ Tool Layer │  │ Data Layer   │
        │            │  │            │  │              │
        │ LLM API    │  │ Payments   │  │ PostgreSQL   │
        │            │  │ Orders     │  │ Redis        │
        └────────────┘  └────────────┘  └──────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────┐
│                    HUMAN SUPPORT LAYER                       │
│                                                              │
│              Agent Dashboard + Agora Takeover                │
└──────────────────────────────────────────────────────────────┘
```

---

# 2. Stack at a Glance

| Layer                  | Technology              | Purpose                             |
| ---------------------- | ----------------------- | ----------------------------------- |
| Web Frontend           | Vite + React            | Main web application (SPA)          |
| UI                     | React                   | Component architecture              |
| Language               | JavaScript (JSX)        | Frontend language                   |
| Styling                | Inline styles / CSS     | UI styling (no CSS framework)       |
| Routing                | react-router-dom        | Client-side SPA routing             |
| Client TTS             | Web Speech API          | Browser speech synthesis            |
| Realtime Communication | Agora                   | Voice/video/realtime infrastructure |
| Conversational AI      | Agora Conversational AI | AI voice participant                |
| Speech-to-Text         | Agora / STT             | Realtime transcription              |
| Text-to-Speech         | Agora / TTS             | AI voice output                     |
| Backend                | FastAPI                 | API + orchestration                 |
| Backend Language       | Python                  | AI/backend logic                    |
| Validation             | Pydantic                | API/data validation                 |
| LLM                    | LiteLLM (pluggable)     | Reasoning + generation              |
| Context                | PostgreSQL              | Persistent support context          |
| Realtime State         | Redis                   | Session state/cache                 |
| Deployment Frontend    | Vercel                  | Web hosting                         |
| Deployment Backend     | Render                  | API hosting                         |
| Realtime               | Agora Cloud             | RTC infrastructure                  |
| Version Control        | Git + GitHub            | Source control                      |
| API Testing            | Postman / Bruno         | API testing                         |
| Monitoring             | Sentry                  | Error tracking                      |
| Logs                   | Structured logging      | Observability                       |

---

# 3. Frontend

## 3.1 Framework

### Vite + React

Vite + React is the primary frontend stack — a lightweight client-side single-page app (SPA).

Responsibilities:

* Application routing
* Client-side rendering (SPA)
* UI composition
* API interaction
* Authentication UI
* Dashboard
* Voice interface
* Agent dashboard

Architecture:

```text
Vite + React
   │
   ├── react-router-dom (client-side routing)
   ├── React (JSX)
   ├── JavaScript
   ├── Inline styles / CSS
   └── agora-rtc-sdk-ng (Agora Web SDK)
```

---

# 4. Frontend Language

## JavaScript

Plain JavaScript (JSX) is used across the entire frontend — there is no TypeScript build step.

Reasons:

* Simple toolchain (Vite + `@vitejs/plugin-react`)
* No type-compilation step to configure or maintain
* Fast iteration for an MVP
* Fewer dependencies
* Lower barrier to contribution

Example:

```js
// Shared conversation-state shape (plain JS object)
const conversationState = {
  sessionId: "",
  state: "IDLE",       // one of the shared PrismState values
  language: "en",
  transcript: "",
  confidence: 0,
};
```

---

# 5. UI Framework

## React

React handles:

* Voice controls
* Conversation interface
* Transcript
* State indicators
* Thinking panel
* Agent dashboard
* Context cards
* Escalation UI

Components should be modular.

Example:

```text
components/
├── voice/
│   ├── VoiceOrb.jsx
│   ├── Transcript.jsx
│   ├── VoiceControls.jsx
│   └── AudioVisualizer.jsx
│
├── conversation/
│   ├── MessageList.jsx
│   ├── MessageBubble.jsx
│   └── ConversationHeader.jsx
│
├── prism/
│   ├── ThinkingPanel.jsx
│   ├── StateIndicator.jsx
│   ├── ContextPanel.jsx
│   └── ConfidenceMeter.jsx
│
└── agent/
    ├── CaseList.jsx
    ├── CaseDetails.jsx
    ├── AgentSummary.jsx
    └── TakeoverButton.jsx
```

---

# 6. Styling

## Inline Styles / CSS

Plain CSS and inline styles are used for the design system — no CSS framework (no Tailwind).

Design philosophy:

```text
Minimal
↓
Black / White / Grey
↓
High contrast
↓
Soft surfaces
↓
Subtle depth
↓
Realtime motion
```

Avoid excessive gradients, excessive shadows, and visual noise.

---

# 7. UI Components

## Hand-built React Components

PRISM's UI is built from hand-written React components styled with inline styles / CSS — there is no third-party component kit.

Typical UI elements:

* Button
* Dialog
* Sheet
* Tabs
* Card
* Badge
* Dropdown
* Tooltip
* Progress
* Toast
* Command
* Scroll area

Components should be customized to match the PRISM design system.

---

# 8. Animation

## CSS Transitions & Animations

CSS transitions and keyframe animations handle interface motion (no animation library).

Use animation for:

* State transitions
* Voice orb
* Transcript appearance
* Thinking indicators
* Panel transitions
* Agent takeover
* Modal transitions
* Page transitions

Animation principle:

> **Motion should explain state, not decorate it.**

Example:

```text
LISTENING
    ↓
UNDERSTANDING
    ↓
THINKING
    ↓
ACTING
    ↓
SPEAKING
```

Each transition should have a subtle visual response.

---

# 9. State Management

For MVP:

### React State

Use:

* `useState`
* `useReducer`
* `useContext`

For more complex global state:

### Zustand

Potential state structure:

```text
prismStore
│
├── session
├── connection
├── conversation
├── transcript
├── prismState
├── toolExecution
├── confidence
└── escalation
```

Avoid introducing Redux unless application complexity genuinely requires it.

---

# 10. Realtime Communication

# Agora

Agora is the **core realtime infrastructure** of PRISM.

It must not be treated as simply a microphone API.

PRISM uses Agora for:

```text
Realtime Voice
      +
AI Participant
      +
Speech Recognition
      +
Speech Synthesis
      +
Realtime Events
      +
Interruption Handling
      +
Human Takeover
```

---

# 11. Agora RTC

The Agora RTC SDK provides the realtime communication foundation.

Primary responsibilities:

* Join channel
* Publish microphone
* Subscribe to remote audio
* Receive AI audio
* Manage participants
* Monitor connection state
* Handle realtime events

Frontend:

```text
User Browser
     ↓
Agora Web SDK
     ↓
PRISM Channel
```

---

# 12. Agora Conversational AI

The AI agent should participate in the Agora channel as a virtual participant.

Architecture:

```text
User
 │
 │ Voice
 ▼
Agora
 │
 ▼
Conversational AI Agent
 │
 ├── STT
 ├── LLM
 ├── Tool Calling
 └── TTS
 │
 ▼
Agora
 │
 ▼
User
```

This allows PRISM to operate as a genuine realtime conversational agent.

---

# 13. Speech-to-Text

Primary:

**Agora Conversational AI / integrated STT**

Fallback:

**Browser Web Speech API**

The fallback is useful for:

* Development
* Browser compatibility
* Demo mode
* Temporary Agora service failures

Partial transcript should be supported where available.

---

# 14. Text-to-Speech

Primary:

**Agora-supported TTS**

The TTS layer should produce realtime AI audio.

Requirements:

* Hindi support
* English support
* Natural pronunciation
* Low latency
* Interruptibility

Browser speech synthesis may be used for lightweight onboarding/greeting scenarios.

---

# 15. Backend

## FastAPI

FastAPI is the primary backend framework.

Responsibilities:

```text
Session Management
       │
       ├── Agora tokens
       ├── Session lifecycle
       └── Participant state

AI Orchestration
       │
       ├── LLM proxy
       ├── Context
       ├── Tool calling
       └── Confidence

Support
       │
       ├── Escalation
       ├── Case creation
       └── Human takeover
```

---

# 16. Backend Language

## Python

Python is used because PRISM's backend is heavily AI-oriented.

Advantages:

* Excellent AI ecosystem
* LLM SDK availability
* FastAPI
* Pydantic
* Async support
* Easy tool orchestration
* Rapid prototyping

---

# 17. API Validation

## Pydantic

All API input/output models should use Pydantic.

Example:

```python
class TransactionCheckRequest(BaseModel):
    transaction_id: str
    amount: float
```

Responses should also use explicit schemas.

---

# 18. Async Architecture

FastAPI endpoints should use asynchronous execution wherever appropriate.

Example:

```text
Request
  ↓
FastAPI
  ↓
Async LLM call
  ↓
Async tool call
  ↓
Response
```

This is important because PRISM is a realtime system.

---

# 19. API Architecture

Recommended structure:

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── session.py
│   │   ├── chat.py
│   │   ├── tools.py
│   │   └── escalation.py
│   │
│   ├── services/
│   │   ├── agora.py
│   │   ├── llm.py
│   │   ├── context.py
│   │   ├── tools.py
│   │   └── escalation.py
│   │
│   ├── models/
│   │   ├── session.py
│   │   ├── conversation.py
│   │   └── support_case.py
│   │
│   ├── schemas/
│   │   ├── session.py
│   │   ├── chat.py
│   │   └── transaction.py
│   │
│   └── core/
│       ├── config.py
│       ├── security.py
│       └── logging.py
│
└── requirements.txt
```

---

# 20. LLM Layer

PRISM should use a **model-agnostic LLM abstraction**.

The backend should not tightly couple business logic to one model provider.

Architecture:

```text
                 PRISM
                   │
                   ▼
              LLM Adapter
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
     Provider A Provider B Provider C
```

Possible providers:

* OpenAI-compatible APIs
* Anthropic-compatible APIs
* Google Gemini
* OpenRouter
* Self-hosted models

The provider should be replaceable through configuration.

PRISM uses **LiteLLM** as the provider adapter. The default model is Groq `openai/gpt-oss-20b`, swappable via configuration.

---

# 21. LLM Responsibilities

The LLM handles:

### Intent Detection

```text
payment_issue
refund_request
account_problem
order_problem
general_support
```

### Entity Extraction

```text
amount
transaction_id
order_id
date
merchant
```

### Conversation Reasoning

Determines what information is missing.

### Tool Selection

Decides whether a tool should be called.

### Response Generation

Produces natural language.

### Escalation Reasoning

Proposes escalation by calling the `escalate_to_human` tool when it judges autonomous resolution unsafe. The LLM does **not** make the final call — a deterministic policy validates every proposal (see §28).

---

# 22. Tool Calling Architecture

Tools should be isolated from the LLM.

```text
LLM
 │
 │ Tool Call
 ▼
Tool Router
 │
 ├── check_transaction
 ├── check_order
 ├── create_ticket
 └── future tools
```

Example:

```python
{
    "name": "check_transaction",
    "arguments": {
        "transaction_id": "TXN123"
    }
}
```

The LLM should never directly manipulate databases or external systems.

---

# 23. Tool Security

Tools must validate:

* Input
* User/session authorization
* Required parameters
* Rate limits
* Tool permissions

The LLM should not be trusted with unrestricted system access.

---

# 24. Context Engine

PRISM maintains two forms of context.

## Short-Term Context

Current conversation.

```text
User message
AI response
Tool result
Current intent
Current state
```

## Structured Case Context

Important facts extracted from the conversation.

```text
Intent
Amount
Transaction ID
Status
Language
Actions
Confidence
Escalation reason
```

---

# 25. Database

## PostgreSQL

PostgreSQL should be the primary persistent database for production.

Store:

* Users
* Sessions
* Conversations
* Support cases
* Tool calls
* Escalations
* Agent actions
* Audit events

Example:

```text
users
sessions
messages
support_cases
tool_calls
escalations
agent_actions
audit_logs
```

---

# 26. Redis

Redis should handle ephemeral realtime state.

Use cases:

* Active sessions
* Session state
* Presence
* Temporary context
* Rate limiting
* Caching
* Pub/Sub

Architecture:

```text
PostgreSQL
   ↓
Persistent state

Redis
   ↓
Realtime / ephemeral state
```

---

# 27. Realtime State Machine

The state machine should be represented explicitly.

```python
class PrismState(str, Enum):
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    LISTENING = "LISTENING"
    UNDERSTANDING = "UNDERSTANDING"
    THINKING = "THINKING"
    ACTING = "ACTING"
    SPEAKING = "SPEAKING"
    ESCALATING = "ESCALATING"
    HUMAN_CONNECTED = "HUMAN_CONNECTED"
    ERROR = "ERROR"
```

This one shared definition lives in `backend/prism_state.py`; the frontend mirror is `frontend/src/config/prismState.js` (identical names, identical order).

---

# 28. Human Escalation Architecture

The LLM does **not** have final authority to escalate. It may only *propose* escalation (by calling the `escalate_to_human` tool); a **deterministic policy** owns the actual decision.

```text
                 LLM
                  │
                  │ proposes escalate_to_human (a tool)
                  ▼
        Deterministic Policy Gate
      (policy.py: evaluate_escalation
        → decision.py: decide)
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
     CONTINUE             ESCALATE
  (policy overrides    (proposal upheld, OR a
   an over-eager        hard trigger fires even
   proposal)            if the LLM never proposed)
        │                    │
        ▼                    ▼
  AI keeps handling     Create Case
                             │
                             ▼
                        Agent Queue
                             │
                             ▼
                        Human Joins
                             │
                             ▼
                         Take Over
```

Two properties define the gate:

* The LLM **cannot** escalate a case the policy deems resolvable — an over-eager proposal is overridden to **CONTINUE**.
* The policy **can** escalate even when the LLM did not propose it, via hard triggers: the user explicitly asks for a human, a contradiction is detected, a tool call fails, or a duplicate charge cannot be verified on a SUCCESS-but-NOT_CONFIRMED transaction.

The LLM handles conversation and understanding; the deterministic engine (`backend/policy.py` → `backend/decision.py`) owns the escalation decision.

---

# 29. Agent Dashboard Stack

Same frontend stack:

```text
Vite
React (JSX)
JavaScript
Inline styles / CSS
react-router-dom
agora-rtc-sdk-ng (Agora Web SDK)
```

The dashboard consumes backend APIs for:

* Cases
* Context
* Transcript
* Tool history
* Escalation status

---

# 30. Human Takeover

Human agents should join the existing communication session.

Preferred architecture:

```text
User
 │
 └──────────────┐
                ▼
             Agora
                ▲
                │
          Human Agent
```

The AI can leave the active speaking role once the agent takes control.

---

# 31. Authentication

MVP:

* Session-based authentication
* Secure Agora token generation
* Server-side API keys
* Environment variables

Production:

* OAuth / OIDC
* JWT/session management
* RBAC
* Organization-level access control

Never expose:

* Agora App Certificate
* LLM API keys
* Database credentials
* Service credentials

to the frontend.

---

# 32. Secrets Management

Environment variables:

```text
AGORA_APP_ID
AGORA_APP_CERTIFICATE
AGORA_CUSTOMER_ID
AGORA_CUSTOMER_SECRET

LLM_API_KEY

DATABASE_URL
REDIS_URL

SENTRY_DSN
```

Secrets must exist only server-side.

---

# 33. Frontend Environment

Only public values should be exposed.

Example:

```text
VITE_API_URL
```

Vite inlines `VITE_`-prefixed variables into the client bundle, so private credentials must never use the `VITE_` prefix. (The Agora App ID is delivered to the client by the backend at session/token time, not via a build-time env var.)

---

# 34. API Endpoints

## Health & Realtime Token

```text
GET  /health                    — liveness probe
GET  /token                     — mint a temporary Agora RTC token (App Certificate stays server-side)
```

## Session

```text
POST /session/start             — start the Agora Conversational AI voice agent for a channel
POST /session/stop              — stop the voice agent
POST /session/reset/{channel}   — reset a channel's in-memory case
```

## Conversation (runs the agent turn: LLM + policy gate)

```text
POST /llm-proxy                 — Agora forwards each realtime voice turn here
POST /chat                      — text-chat turn (same agent turn)
```

## Cases (agent dashboard)

```text
GET  /cases                     — list escalated cases
GET  /cases/{case_id}           — one escalated case
POST /cases/{case_id}/takeover  — human agent takes over a case
```

## State

```text
GET  /state/{channel}           — live PrismState + ai_state + transcript for a channel
GET  /active-state              — same shape, for the most-recently-active channel
GET  /debug/case/{channel}      — debug dump of a channel's case
```

## Mock Data

```text
GET  /mock/transaction/{tx_id}  — mock transaction lookup (demo data)
```

## Speech (optional; requires torch)

```text
POST /asr                       — Faster-Whisper transcription
GET  /asr/status                — ASR availability
WS   /ws/vad                    — Silero VAD barge-in stream
```

---

# 35. API Communication

Frontend → Backend:

**REST**

Used for:

* Session management
* Tool requests
* Case management
* Authentication
* Configuration

Realtime:

**Agora**

Used for:

* Audio
* Voice
* AI participant
* Realtime communication events

Future:

**WebSocket / SSE**

Can be used for:

* Backend state updates
* Agent queue updates
* Live case events

---

# 36. Deployment

## Frontend

### Vercel

Deployment:

```text
GitHub
   ↓
Vercel
   ↓
Vite build → dist (static SPA)
```

Build: `npm run build` (output `dist`); env: `VITE_API_URL`.

Benefits:

* CI/CD
* Preview deployments
* Edge/CDN
* Simple static SPA deployment

---

# 37. Backend

### Render

Deployment:

```text
GitHub
   ↓
Render
   ↓
FastAPI
```

For MVP/demo purposes, Render provides simple backend deployment. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` (Python 3.11).

Production architecture can later move to:

* AWS
* GCP
* Azure
* Kubernetes

depending on scale.

---

# 38. Render Keep-Alive

If the selected Render configuration sleeps after inactivity, the frontend can periodically call:

```http
GET /health
```

Example:

```text
Every ~5 minutes
       ↓
/health
       ↓
Backend stays warm
```

This is a **demo/MVP optimization**, not a production scaling strategy.

---

# 39. CI/CD

Recommended:

```text
GitHub
  │
  ├── Pull Request
  │      ↓
  │   Tests
  │      ↓
  │   Build
  │
  └── Main
         ↓
       Deploy
```

Frontend:

**GitHub → Vercel**

Backend:

**GitHub → Render**

---

# 40. Testing

## Frontend

Recommended:

* Vitest
* React Testing Library
* Playwright

Test:

* Components
* State transitions
* Voice UI
* Agent dashboard
* User flows

---

## Backend

Recommended:

* Pytest
* HTTPX

Test:

* API endpoints
* Tool execution
* Context engine
* Escalation
* LLM adapter
* Authentication

---

# 41. Realtime Testing

Realtime functionality should be tested separately from normal API tests.

Test:

```text
Join Agora
    ↓
Publish audio
    ↓
AI joins
    ↓
Speech detected
    ↓
Transcript
    ↓
LLM
    ↓
Tool
    ↓
TTS
    ↓
Audio response
```

Also test:

* User interruption
* Connection loss
* AI timeout
* Agent takeover
* Reconnection

---

# 42. Observability

## Sentry

Use Sentry for:

* Frontend errors
* Backend exceptions
* Performance monitoring

---

## Structured Logs

Every important event should include:

```json
{
  "timestamp": "...",
  "session_id": "...",
  "event": "tool_call",
  "tool": "check_transaction",
  "latency_ms": 421
}
```

---

# 43. Metrics

Track:

```text
Session count
Active sessions
Average latency
LLM latency
STT latency
TTS latency
Tool latency
Resolution rate
Escalation rate
Tool failure rate
AI interruption rate
Human takeover rate
```

---

# 44. Security Architecture

PRISM should follow a **zero-trust approach toward AI actions**.

The LLM is not authorized to directly:

* Access databases
* Execute arbitrary code
* Call arbitrary URLs
* Modify system files
* Access credentials

Instead:

```text
LLM
 ↓
Validated Tool
 ↓
Authorization
 ↓
Execution
 ↓
Verified Result
```

---

# 45. Privacy

Conversation data should be treated as potentially sensitive.

Requirements:

* Encrypt data in transit
* Encrypt sensitive persistent data
* Minimize stored PII
* Implement retention policies
* Restrict agent access
* Maintain audit logs

Production deployments should add appropriate regulatory/compliance controls for the target industry.

---

# 46. Rate Limiting

Apply rate limits to:

* Session creation
* Chat endpoint
* Tool execution
* Authentication
* Agent actions

Redis can be used for distributed rate limiting.

---

# 47. Caching

Cache:

* Static configuration
* Language configuration
* Non-sensitive metadata
* Frequently accessed support information

Do **not** blindly cache sensitive transaction information.

---

# 48. Language Architecture

The language layer should be configurable.

```text
languages/
├── en
├── hi
└── config
```

MVP:

```text
English
Hindi
Hinglish
```

Future:

```text
Bengali
Telugu
Marathi
Tamil
Gujarati
Kannada
Malayalam
Punjabi
Odia
Assamese
Urdu
...
```

The architecture should allow additional languages without rewriting the conversation engine.

---

# 49. Project Structure

Recommended monorepo:

```text
prism/
│
├── apps/
│   │
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── stores/
│   │   └── types/
│   │
│   └── backend/
│       ├── app/
│       ├── tests/
│       └── requirements.txt
│
├── packages/
│   ├── types/
│   ├── config/
│   └── ui/
│
├── docs/
│   ├── PRD.md
│   ├── TECH_STACK.md
│   ├── ARCHITECTURE.md
│   └── API.md
│
├── .env.example
├── README.md
└── package.json
```

---

# 50. MVP Technology Choices

The actual hackathon implementation should remain lean.

### Required

```text
Vite
React (JSX)
JavaScript
Inline styles / CSS
react-router-dom
agora-rtc-sdk-ng (Agora Web SDK)

FastAPI
Python 3.11
Pydantic
uvicorn
httpx

Agora
Agora Conversational AI

LiteLLM (default Groq openai/gpt-oss-20b)

Vercel
Render
GitHub
```

### Optional / Add When Needed

```text
PostgreSQL
Redis
Sentry
Playwright
Pytest
faster-whisper / silero-vad / torch (for /asr + /ws/vad)
```

Do not introduce infrastructure simply because it exists.

---

# 51. Why This Stack?

## Why Vite + React?

Fast dev server with hot module replacement, a lightweight client-side single-page app, client-side routing via react-router-dom, and a simple static build (`dist`) deployed to Vercel.

## Why JavaScript?

Keeps the toolchain and build simple — no type-compilation step — for fast MVP iteration with fewer dependencies.

## Why FastAPI?

Fast Python backend with excellent async and AI ecosystem support.

## Why Agora?

PRISM's defining feature is realtime communication.

Agora provides the communication infrastructure required to make the AI a realtime participant rather than simply a REST chatbot.

## Why PostgreSQL?

Reliable relational persistence for support cases and conversation data.

## Why Redis?

Fast ephemeral state for realtime sessions.

## Why a pluggable LLM?

PRISM should not become dependent on a single model provider.

---

# 52. Technology Decision Matrix

| Requirement      | Technology              |
| ---------------- | ----------------------- |
| Web UI           | Vite + React (SPA)      |
| Mobile future    | React Native / Expo     |
| UI               | React                   |
| Language         | JavaScript (JSX)        |
| Styling          | Inline styles / CSS     |
| Routing          | react-router-dom        |
| Client TTS       | Web Speech API          |
| Voice            | Agora                   |
| RTC              | Agora RTC               |
| AI Voice Agent   | Agora Conversational AI |
| STT              | Agora-integrated STT    |
| TTS              | Agora-integrated TTS    |
| Backend          | FastAPI                 |
| Backend Language | Python                  |
| Validation       | Pydantic                |
| AI               | LiteLLM (Groq default)  |
| Persistent DB    | PostgreSQL              |
| Cache            | Redis                   |
| Frontend Hosting | Vercel                  |
| Backend Hosting  | Render                  |
| Source Control   | GitHub                  |
| Monitoring       | Sentry                  |
| API Testing      | Postman / Bruno         |
| E2E Testing      | Playwright              |
| Backend Testing  | Pytest                  |

---

# 53. Architecture Evolution

## Hackathon

```text
Vite + React
   +
FastAPI
   +
Agora
   +
LLM
   +
Mock Tools
```

Keep it simple.

---

## Early Production

```text
Vite + React
      +
FastAPI
      +
Agora
      +
PostgreSQL
      +
Redis
      +
LLM Gateway
      +
Real Support APIs
```

---

## Scale

```text
                    Load Balancer
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
         API Node      API Node      API Node
             │            │            │
             └────────────┼────────────┘
                          │
                    Service Layer
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
       Redis         PostgreSQL       Event Bus
          │                                │
          └───────────────┬────────────────┘
                          ▼
                    AI Services
                          │
                    Agora Cloud
```

---

# 54. Critical Engineering Rule

### Agora should remain central.

Do not build PRISM as:

```text
Browser microphone
       ↓
REST API
       ↓
LLM
       ↓
Browser audio
```

That would reduce Agora to a superficial integration.

The intended architecture is:

```text
                 AGORA
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
      USER       AI AGENT   HUMAN
        │          │          │
        └──────────┼──────────┘
                   │
             PRISM BRAIN
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
      CONTEXT     TOOLS    CONFIDENCE
```

Agora is the **communication fabric** connecting the participants.

PRISM is the **intelligence layer** controlling the conversation.

---

# 55. Final Technical Philosophy

PRISM should be built as a **realtime system first and an AI application second**.

The architecture therefore separates four major responsibilities:

```text
AGORA
Realtime communication
        ↓
PRISM
Conversation intelligence
        ↓
TOOLS
Real-world actions
        ↓
HUMANS
Safe escalation
```

The result is a system where:

**Agora connects.**

**AI understands.**

**Context remembers.**

**Tools act.**

**Verification prevents hallucination.**

**Confidence decides.**

**Humans take over when necessary.**

That separation is the foundation of PRISM's technical architecture.
