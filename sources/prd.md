# PRISM

## Polyglot Real-time Intelligent Support Mediator

**Product Requirements Document · v1.0**

---

## 1. Product Overview

### 1.1 Product Name

**PRISM**

**Full Form:** Polyglot Real-time Intelligent Support Mediator

### 1.2 Product Category

Real-time AI voice support and human-escalation platform.

### 1.3 One-Line Description

> **PRISM is a real-time, multilingual AI support agent that listens, understands, acts, verifies, and escalates to a human without losing the conversation context.**

### 1.4 Core Problem

Traditional customer-support systems force users through rigid IVR menus, repetitive questions, language barriers, and disconnected human handoffs.

When an AI cannot confidently solve a problem, the conversation often breaks:

**AI → "I can't help you." → User starts over with human agent.**

PRISM changes this to:

**User → AI understands → AI investigates → AI acts → AI verifies → AI escalates with full context when necessary.**

The human agent receives the case, not a blank conversation.

---

# 2. Vision

PRISM aims to become a **real-time intelligence layer between people and support systems**.

Instead of treating voice as merely an input channel, PRISM treats the entire conversation as a continuously evolving state.

The system should understand:

* What the user said
* What they mean
* What has already been established
* What information is missing
* What actions are possible
* How confident the AI is
* When it should stop acting autonomously
* What a human agent needs to know

### Vision Statement

> **Make support conversations feel like talking to an intelligent human who remembers everything, speaks your language, can actually take action, and knows when to hand you over.**

---

# 3. Target Users

## Primary User: Customer / Caller

A person contacting support through voice.

Typical problems:

* Payment failed
* Money was deducted
* Transaction is pending
* Account problem
* Service issue
* Refund request
* General assistance

The user should be able to speak naturally rather than navigate menus.

---

## Secondary User: Human Support Agent

A support representative who receives escalated conversations.

The agent needs:

* Conversation summary
* Customer intent
* Verified information
* Missing information
* Actions already performed
* Tool results
* AI confidence
* Reason for escalation
* Relevant conversation transcript
* Ability to take over immediately

---

## Tertiary User: Support Organization

Organizations using PRISM to automate repetitive support interactions while preserving human intervention for complex cases.

---

# 4. Problem Statement

Current support systems suffer from five major problems.

### 4.1 Rigid Interaction

Traditional IVR:

> Press 1 for English
> Press 2 for Hindi
> Press 3 for payments

PRISM:

> "Bhai mera payment kat gaya but order confirm nahi hua."

The user speaks naturally.

---

### 4.2 Language Barrier

Users may switch between:

* Hindi
* English
* Hinglish
* Code-switched sentences

Example:

> "Mera payment deduct ho gaya but transaction abhi pending dikha raha hai."

PRISM should understand the meaning without forcing the user into a predefined language structure.

---

### 4.3 Repetition

Users frequently have to repeat information after being transferred to a human.

PRISM preserves the context.

---

### 4.4 AI Hallucination

An AI support system should never invent transaction results or claim that an action happened when it did not.

PRISM therefore introduces:

**Confidence-aware decision making.**

---

### 4.5 Poor AI → Human Handoff

Traditional escalation:

> "Connecting you to an agent..."

PRISM escalation:

> "Payment of ₹2,499 was reported as deducted. Transaction ID verified. Status could not be confirmed. AI confidence: 61%. User has already provided the required transaction details."

The human starts where the AI stopped.

---

# 5. Product Principles

PRISM is built around six principles.

### 1. Voice First

Voice is a primary interface, not an afterthought.

### 2. Context First

Every interaction contributes to a structured case state.

### 3. Action Over Conversation

The AI should solve problems, not merely talk about them.

### 4. Confidence Over Ego

If the AI is uncertain, it should stop pretending.

### 5. Human Escalation Is a Feature

Human intervention is part of the architecture, not a failure state.

### 6. Real-Time by Design

The entire experience should feel conversational and immediate.

---

# 6. Core Product Loop

PRISM operates through the following loop:

**LISTEN → UNDERSTAND → REMEMBER → DECIDE → ACT → VERIFY → RESOLVE / ESCALATE**

### LISTEN

Capture real-time user speech.

### UNDERSTAND

Convert speech into structured intent and meaning.

### REMEMBER

Maintain conversation and case context.

### DECIDE

Determine the next best action.

### ACT

Call tools or support APIs when necessary.

### VERIFY

Confirm whether the action actually succeeded.

### RESOLVE

Provide the user with a grounded answer.

### ESCALATE

If the AI cannot safely resolve the case, transfer it to a human with context.

---

# 7. MVP Scope

The MVP focuses on one high-value vertical:

## Payment Support

Example scenario:

> User says their payment was deducted but the transaction/order is not confirmed.

The MVP demonstrates the complete intelligence loop.

### MVP Flow

```text
User speaks
     ↓
Agora real-time voice
     ↓
Speech recognition
     ↓
PRISM AI
     ↓
Intent + context extraction
     ↓
Confidence evaluation
     ↓
Transaction tool
     ↓
Transaction verification
     ↓
┌─────────────────────┐
│                     │
│  Resolved           │
│       OR            │
│  Escalate           │
│                     │
└─────────────────────┘
     ↓
Human Agent
     ↓
Context-preserved takeover
```

---

# 8. Core Features

## 8.1 Real-Time Voice Conversation

Users interact with PRISM naturally through voice.

Requirements:

* Real-time microphone input
* Real-time AI audio response
* Low conversational latency
* Interruptible AI responses
* Turn detection
* Continuous conversation state

---

# 9. Agora Integration

Agora is a **core infrastructure layer** of PRISM.

It is not merely used as a microphone transport mechanism.

PRISM should leverage Agora for:

* Real-time audio
* Voice channel infrastructure
* AI agent participation
* Speech-to-text
* Text-to-speech / AI audio delivery
* Conversation events
* Turn detection
* Interruption handling
* Agent participation
* Human takeover
* Real-time communication state

### Architecture

```text
                 ┌──────────────────┐
                 │      User        │
                 │  Voice / Mobile  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │      Agora       │
                 │  Realtime Layer  │
                 └────────┬─────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        Speech / Events          AI Agent
              │                       │
              └───────────┬───────────┘
                          ▼
                  ┌──────────────┐
                  │    PRISM     │
                  │ Intelligence │
                  └──────┬───────┘
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          Context      Tools      Confidence
             │           │           │
             └───────────┼───────────┘
                         ▼
                    Resolution
                         │
                  ┌──────┴──────┐
                  ▼             ▼
               Resolve       Escalate
                                │
                                ▼
                         Human Agent
```

---

# 10. Multilingual Intelligence

PRISM supports natural multilingual conversation.

### Priority Languages

**Hindi + English**

With support for:

**Hinglish / code-switching**

Example:

> "Mera payment deduct ho gaya but refund kab tak aayega?"

The AI should understand the semantic meaning rather than treating language switching as an error.

---

# 11. Live Transcription

While the user is speaking, PRISM should display partial transcription.

Example:

```text
LISTENING...

"bhai mera payment kat gaya..."
```

Then:

```text
"bhai mera payment kat gaya but order confirm..."
```

Then:

```text
"bhai mera payment kat gaya but order confirm nahi hua"
```

This provides visual confirmation that PRISM is listening.

---

# 12. Conversation State Machine

PRISM maintains an explicit real-time state.

### States

```text
IDLE
 ↓
CONNECTING
 ↓
LISTENING
 ↓
UNDERSTANDING
 ↓
THINKING
 ↓
ACTING
 ↓
SPEAKING
 ↓
LISTENING
```

Alternative paths:

```text
THINKING
   ↓
ESCALATING
   ↓
HUMAN_CONNECTED
```

### State Definitions

| State           | Meaning                      |
| --------------- | ---------------------------- |
| IDLE            | No active conversation       |
| CONNECTING      | Establishing Agora session   |
| LISTENING       | User is speaking             |
| UNDERSTANDING   | Speech is being interpreted  |
| THINKING        | AI is deciding what to do    |
| ACTING          | Tool/API action is executing |
| SPEAKING        | AI is responding             |
| ESCALATING      | Human handoff is occurring   |
| HUMAN_CONNECTED | Human agent has taken over   |
| ERROR           | Unrecoverable error          |

---

# 13. Conversation Context Engine

PRISM converts unstructured conversation into structured state.

Example:

```json
{
  "intent": "payment_issue",
  "problem": "payment_deducted_order_not_confirmed",
  "amount": 2499,
  "currency": "INR",
  "transaction_id": "TXN_12345",
  "user_language": "hinglish",
  "transaction_status": "unknown",
  "verified_information": [],
  "missing_information": [],
  "confidence": 0.72
}
```

The context should continuously update throughout the conversation.

---

# 14. Intelligent Questioning

PRISM should not ask unnecessary questions.

Instead, it identifies what information is missing.

Example:

User:

> "Payment kat gaya."

PRISM:

> "Kitne amount ka payment tha?"

After amount:

> "Transaction ID mil sakti hai?"

The system should ask the **next best question** based on the current state.

---

# 15. Tool Calling

PRISM can perform actions through tools.

### MVP Tool

`check_transaction`

Example:

```text
Input:
transaction_id
amount

Output:
transaction_status
transaction_timestamp
verification_result
```

Possible results:

```text
SUCCESS
PENDING
FAILED
NOT_FOUND
UNKNOWN
```

---

# 16. Grounded Responses

PRISM must distinguish between:

### Known

Information returned by tools or explicitly provided by the user.

### Unknown

Information that cannot currently be verified.

### Inferred

Information the AI believes may be true but cannot confirm.

The AI must never convert an inference into a fact.

Example:

Bad:

> "Your refund will arrive tomorrow."

Good:

> "The transaction is currently pending. I can't confirm the refund time yet."

---

# 17. Confidence Engine

Every important AI decision should have an associated confidence level.

Example:

```text
Intent confidence:       94%
Transaction confidence:  87%
Resolution confidence:   42%
```

The system can use confidence to determine whether it should continue autonomously.

### High Confidence

AI can resolve.

### Medium Confidence

AI asks another clarifying question.

### Low Confidence

AI escalates.

---

# 18. Human Escalation

Escalation is triggered when:

* AI confidence is too low
* Required information cannot be verified
* Tool result is ambiguous
* User explicitly requests a human
* The issue exceeds AI capabilities
* Repeated clarification fails

### Escalation Decision (Validated Gate)

The LLM does **not** have final authority to escalate. Escalation is a validated gate:

**LLM proposes `escalate_to_human` → a deterministic policy validates the proposal → the policy returns ESCALATE or CONTINUE.**

The deterministic policy (`backend/policy.py` → `evaluate_escalation`, which calls `backend/decision.py` → `decide`) is the single source of truth for whether a case is genuinely escalation-worthy:

* The LLM **cannot** escalate a case the policy considers resolvable — the policy overrides an over-eager proposal with CONTINUE.
* The policy **can** escalate even when the LLM did not propose it, on hard triggers: the user explicitly asks for a human, a contradiction is detected, a verification tool fails, or a duplicate charge cannot be confirmed on a completed transaction.

The LLM handles conversation and understanding; the deterministic engine owns the escalation decision.

### Escalation Flow

```text
LLM proposes escalation (or a hard trigger fires)
        ↓
Deterministic policy validates → ESCALATE
        ↓
Create support case
        ↓
Generate structured summary
        ↓
Attach conversation context
        ↓
Notify human agent
        ↓
Human joins
        ↓
AI exits / becomes observer
```

---

# 19. Human Agent Dashboard

The human agent should see a structured case rather than raw conversation alone.

### Dashboard

```text
┌─────────────────────────────────────────────┐
│ CUSTOMER                                    │
│ Payment Issue                               │
├─────────────────────────────────────────────┤
│                                             │
│ SUMMARY                                     │
│ Payment deducted but order not confirmed.  │
│                                             │
│ VERIFIED                                    │
│ ✓ Amount: ₹2,499                            │
│ ✓ Transaction ID                            │
│ ✓ User identity/session                     │
│                                             │
│ MISSING                                     │
│ • Merchant confirmation                     │
│                                             │
│ AI CONFIDENCE                               │
│ 61%                                         │
│                                             │
│ ACTIONS                                     │
│ ✓ Transaction checked                       │
│                                             │
│ REASON FOR ESCALATION                       │
│ Transaction status could not be verified.  │
│                                             │
│ [ TAKE OVER ]                               │
└─────────────────────────────────────────────┘
```

---

# 20. Context-Preserving Handoff

When the human takes over:

The user should **not** have to repeat their problem.

The agent receives:

* Conversation summary
* Transcript
* User intent
* Important entities
* Transaction information
* Tool results
* AI actions
* Confidence
* Escalation reason

---

# 21. Human Takeover

Human takeover should be seamless.

### Before

```text
AI Agent
   ↓
Agora Channel
```

### After

```text
Human Agent
   ↓
Agora Channel
   ↑
User
```

The transition should preserve the active communication session wherever technically possible.

---

# 22. Text Chat Fallback

The system should provide a text interaction fallback.

Useful when:

* Microphone permission is denied
* User cannot speak
* Browser audio fails
* Demonstration fallback is needed

Text should use the same PRISM intelligence layer and conversation context.

---

# 23. UI / UX Requirements

PRISM should visually communicate **intelligence, state, and realtime activity** without overwhelming the user.

### Primary Interface

A dashboard-based interface with:

1. Conversation area
2. Realtime voice state
3. Live transcript
4. AI thinking/action state
5. Context panel
6. Escalation status
7. Human-agent interface

---

# 24. Visual Language

The UI should feel:

* Minimal
* Premium
* Modern
* Technical
* Calm
* Realtime
* SaaS-oriented

The visual system should avoid excessive decoration.

Focus on:

**Black / white / grey**

with subtle state indicators.

Animations should communicate system state rather than exist purely for decoration.

---

# 25. Realtime Visual Feedback

The user should always understand what PRISM is doing.

Examples:

### Listening

```text
● LISTENING
```

### Understanding

```text
◌ UNDERSTANDING
```

### Thinking

```text
◌ THINKING
```

### Checking transaction

```text
✓ CHECKING TRANSACTION
```

### Speaking

```text
◉ SPEAKING
```

### Escalating

```text
↗ CONNECTING HUMAN AGENT
```

---

# 26. Primary User Journey

## Step 1: Start

User opens PRISM.

```text
"How can I help you?"
```

---

## Step 2: User Speaks

> "Bhai mera payment kat gaya but order confirm nahi hua."

---

## Step 3: PRISM Understands

```text
Intent:
Payment Issue

Sub-intent:
Payment deducted / order not confirmed

Language:
Hinglish
```

---

## Step 4: PRISM Collects Missing Information

> "Kitne amount ka payment tha?"

User:

> "2499."

---

## Step 5: Transaction Check

PRISM asks for / extracts transaction information.

Then calls:

```text
check_transaction()
```

---

## Step 6: Verify

Tool returns:

```text
Status: UNKNOWN
```

PRISM does not invent a result.

---

## Step 7: Escalate

PRISM says:

> "Main is transaction ko completely verify nahi kar pa raha hoon. Main aapko human support agent se connect karta hoon aur unhe ab tak ki saari information de deta hoon."

---

## Step 8: Human Agent

Agent immediately receives:

```text
Payment issue
₹2,499
Transaction ID
Tool result
Conversation transcript
AI summary
Escalation reason
```

---

# 27. Functional Requirements

## FR-01: Voice Session

System must allow a user to start and end a realtime voice session.

## FR-02: Agora Channel

System must create/join an Agora realtime communication channel.

## FR-03: AI Participant

The AI agent must be able to participate as a realtime participant.

## FR-04: Speech Recognition

System must convert user speech into text.

## FR-05: Partial Transcript

System should display partial speech transcription where supported.

## FR-06: Multilingual Understanding

System must support Hindi, English and Hinglish.

## FR-07: Context

System must maintain structured conversation context.

## FR-08: Intent Detection

System must identify the user's primary support intent.

## FR-09: Missing Information

System must identify information required to continue.

## FR-10: Tool Calling

System must call external/mock support tools.

## FR-11: Verification

System must validate tool results before claiming resolution.

## FR-12: Confidence

System must maintain decision/resolution confidence.

## FR-13: Escalation

System must trigger human escalation when configured conditions are met.

## FR-14: Case Creation

System must create an escalation case containing conversation context.

## FR-15: Agent Dashboard

Human agents must be able to view escalated cases.

## FR-16: Human Takeover

Agent must be able to take over the conversation.

## FR-17: Text Fallback

User must be able to interact through text when voice is unavailable.

---

# 28. Non-Functional Requirements

### Latency

Conversation should feel realtime.

Target:

**< 1–2 seconds perceived response latency** where infrastructure permits.

### Reliability

If one AI/tool component fails, the user should receive a graceful fallback rather than a broken interface.

### Security

Sensitive customer information should not be exposed unnecessarily.

### Observability

The system should log:

* Session ID
* Conversation state
* Tool calls
* Tool results
* Escalation events
* Errors
* Latency

### Scalability

The architecture should allow multiple concurrent sessions in future versions.

---

# 29. Technical Architecture

## Frontend

**Vite + React (JavaScript / JSX)**

A lightweight client-side single-page application. Vite provides a fast dev server with hot module replacement; React is written in plain JavaScript (JSX, not TypeScript). Client-side routing is handled by `react-router-dom`, styling is plain inline styles / CSS (no Tailwind or other CSS framework), the realtime client uses the Agora Web SDK (`agora-rtc-sdk-ng`), and AI audio is spoken via the browser's native Web Speech API (`window.speechSynthesis`). The static build is deployed to Vercel. This is a client-side SPA — there is no server-side rendering or server components.

Responsibilities:

* Voice interface
* Agora client
* Live transcript
* State visualization
* Conversation UI
* Agent dashboard
* Context visualization

---

## Backend

**FastAPI** (Python 3.11)

Runs with `uvicorn backend.main:app` (local dev port 8001) and is deployed to Render.

Responsibilities:

* Session management
* Agora token generation
* Agora REST APIs
* LLM proxy
* Tool execution
* Context management
* Escalation
* Case management

---

## Realtime Layer

**Agora**

Responsibilities:

* Realtime audio
* AI participant
* Conversational AI
* STT
* TTS/audio delivery
* Events
* Interruption handling
* Human takeover communication

---

## Intelligence Layer

LLM-based reasoning engine.

Responsibilities:

* Intent classification
* Context extraction
* Question generation
* Decision making
* Tool selection
* Response generation
* Escalation *proposal* (validated by the deterministic policy gate)

---

## Tool Layer

MVP:

```text
check_transaction()
```

Future:

```text
check_order()
initiate_refund()
cancel_transaction()
check_account()
create_ticket()
```

---

# 30. API Requirements

The backend is a FastAPI service (local dev port **8001**). It exposes the following endpoints.

### Health & Token

```http
GET /health
```

Liveness probe. Returns `{"status":"ok","service":"prism-backend"}`.

```http
GET /token
```

Mints a temporary Agora RTC token (the App Certificate stays server-side).

---

### Voice Session

```http
POST /session/start
```

Starts the Agora Conversational AI voice agent for a channel.

```http
POST /session/stop
```

Stops the voice agent.

```http
POST /session/reset/{channel}
```

Resets a channel's in-memory case.

---

### Agent Turn

```http
POST /llm-proxy
```

Agora forwards each realtime voice turn here; runs the agent turn (LLM + deterministic policy gate).

```http
POST /chat
```

Text-chat turn; runs the same agent turn.

---

### Cases (Agent Dashboard)

```http
GET /cases
```

Lists escalated cases.

```http
GET /cases/{case_id}
```

Returns one escalated case.

```http
POST /cases/{case_id}/takeover
```

Human agent takes over a case.

---

### Live State

```http
GET /state/{channel}
```

Live PrismState + ai_state + transcript for a specific channel.

```http
GET /active-state
```

Same shape, for the most-recently-active channel (the dashboard follows the active channel).

```http
GET /debug/case/{channel}
```

Debug dump of a channel's case.

---

### Transaction & Speech

```http
GET /mock/transaction/{tx_id}
```

Mock transaction lookup (demo data).

```http
POST /asr
```

Faster-Whisper transcription (optional; requires torch).

```http
GET /asr/status
```

ASR availability.

```http
WS /ws/vad
```

Silero VAD barge-in stream (optional; requires torch).

---

# 31. Data Model

### Session

```json
{
  "session_id": "...",
  "channel_id": "...",
  "user_id": "...",
  "language": "hinglish",
  "state": "THINKING",
  "created_at": "..."
}
```

### Support Case

```json
{
  "case_id": "...",
  "session_id": "...",
  "intent": "payment_issue",
  "summary": "...",
  "verified_data": {},
  "missing_data": [],
  "actions": [],
  "confidence": 0.61,
  "escalation_reason": "...",
  "status": "waiting_for_agent"
}
```

---

# 32. Error Handling

### Agora failure

Show:

```text
Unable to establish realtime connection.
```

Provide text fallback.

### LLM failure

Use controlled fallback response.

### Tool failure

Do not claim success.

### STT failure

Ask user to repeat or switch to text.

### TTS failure

Display the response as text.

### Human agent unavailable

Create a support case and provide a fallback path.

---

# 33. MVP Success Criteria

The MVP is successful if a judge can perform the following sequence:

1. Open PRISM
2. Start a voice session
3. Speak naturally
4. Speak in Hindi/English/Hinglish
5. See realtime interaction
6. Observe AI understanding
7. Provide transaction information
8. Watch PRISM call a tool
9. See the tool result
10. See PRISM avoid making an unsupported claim
11. Trigger escalation
12. Open the human agent dashboard
13. See the complete context
14. Take over the conversation

The entire flow should feel like **one continuous conversation**.

---

# 34. Demo Scenario

### User

> "Mera payment deduct ho gaya hai lekin order confirm nahi hua."

### PRISM

Identifies:

```text
Intent: Payment Issue
Language: Hindi/Hinglish
```

### PRISM

> "Kitne amount ka payment tha?"

### User

> "2499 rupees."

### PRISM

Checks transaction.

```text
CHECKING TRANSACTION...
```

### Tool

```text
Transaction found
Status: Pending
```

### PRISM

> "Aapka payment abhi pending hai. Main transaction details verify kar raha hoon."

If verification succeeds:

```text
RESOLVED
```

If verification becomes uncertain:

```text
ESCALATING...
```

### Human Agent

Receives:

```text
PAYMENT ISSUE

Amount: ₹2,499
Status: Pending
Intent confidence: 96%
Resolution confidence: 54%

AI ACTIONS:
✓ Transaction lookup

ESCALATION:
Unable to guarantee final payment resolution.

[TAKE OVER]
```

---

# 35. Out of Scope for MVP

The MVP deliberately does **not** attempt to solve everything.

Excluded:

* Multiple industries
* Complex authentication
* Production-grade banking integrations
* Multiple AI agents
* Advanced fraud detection
* Sophisticated ML confidence models
* Complex CRM integrations
* Large-scale database architecture
* Advanced noise cancellation
* Fully autonomous refunds
* Large multilingual expansion
* Enterprise billing
* Advanced analytics

These can be added after proving the core interaction loop.

---

# 36. Future Roadmap

## Phase 1: MVP

**Payment support**

```text
Voice
+
Hindi / English / Hinglish
+
Context
+
Transaction tool
+
Confidence
+
Human escalation
```

---

## Phase 2: Support Platform

Add:

* Order support
* Refunds
* Account support
* Ticket creation
* CRM integrations
* Support analytics

---

## Phase 3: Intelligence Platform

Add:

* Long-term customer context
* Personalized support
* Advanced confidence modeling
* Automatic issue categorization
* Predictive escalation
* Agent performance analytics
* Conversation intelligence

---

## Phase 4: Enterprise PRISM

Add:

* Multi-tenant architecture
* Organization-specific knowledge bases
* Custom workflows
* Custom tools
* Role-based access
* Enterprise analytics
* Compliance controls
* Integration marketplace

---

# 37. Key Product Metrics

### AI Resolution Rate

Percentage of conversations resolved without human intervention.

### Escalation Accuracy

Percentage of escalations where human intervention was actually necessary.

### Context Preservation Rate

Percentage of escalated conversations where the agent has sufficient information to continue without asking the user to repeat themselves.

### Tool Success Rate

Percentage of tool calls that successfully produce usable results.

### First-Response Latency

Time from user turn completion to AI response.

### Average Resolution Time

Average time required to resolve a support case.

### User Repetition Rate

How often users need to repeat previously provided information.

---

# 38. Competitive Differentiation

PRISM is not simply:

**Chatbot + microphone.**

It is:

```text
REALTIME COMMUNICATION
          +
CONVERSATIONAL AI
          +
CONTEXT ENGINE
          +
ACTION / TOOLS
          +
CONFIDENCE
          +
HUMAN HANDOFF
```

The differentiator is the **closed-loop support architecture**.

Most systems optimize either:

**AI conversation**

or

**human support.**

PRISM connects the two.

---

# 39. Product North Star

The north-star experience is:

> **A user should be able to start speaking naturally, in their own language, explain a problem once, have PRISM investigate and act on it, and if a human is needed, be transferred without starting the conversation over.**

---

# 40. PRISM in One Diagram

```text
                    ┌─────────────────┐
                    │      USER       │
                    │ Voice / Text    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     AGORA       │
                    │ Realtime Layer  │
                    └────────┬────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   PRISM INTELLIGENCE │
                  │                      │
                  │ Listen               │
                  │ Understand           │
                  │ Remember             │
                  │ Decide               │
                  │ Act                  │
                  │ Verify               │
                  └──────────┬───────────┘
                             │
               ┌─────────────┼─────────────┐
               ▼             ▼             ▼
          ┌─────────┐   ┌─────────┐   ┌──────────┐
          │ Context │   │  Tools  │   │Confidence│
          │ Engine  │   │ Engine  │   │  Engine  │
          └────┬────┘   └────┬────┘   └─────┬────┘
               └─────────────┼───────────────┘
                             ▼
                    ┌─────────────────┐
                    │     DECISION    │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
          ┌─────────────┐         ┌─────────────┐
          │   RESOLVE   │         │   ESCALATE  │
          └─────────────┘         └──────┬──────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │  HUMAN AGENT    │
                                │                 │
                                │ Context         │
                                │ Summary         │
                                │ Transcript      │
                                │ Tool Results    │
                                │ Confidence      │
                                └─────────────────┘
```

---

# 41. Final Product Definition

**PRISM is a realtime AI support mediator that sits between customers and support teams.**

It does not merely answer questions.

It:

**listens → understands → remembers → decides → acts → verifies → resolves or escalates.**

And when escalation happens, the AI does not disappear and leave the user to start again.

It hands the human **the entire case context**.

That is the core product.
