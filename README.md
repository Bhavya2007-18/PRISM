PRISM

An AI support agent that knows when it doesn't know.

PRISM is an uncertainty-aware, multilingual AI customer-support system designed to resolve customer issues automatically when it has enough confidence, and intelligently escalate to a human when it doesn't.

Unlike traditional AI support systems that focus primarily on generating an answer, PRISM focuses on a more important question:

"Do I have enough evidence to trust this conclusion?"

When PRISM is confident, it can continue assisting the customer. When it is uncertain, it doesn't guess. It identifies the uncertainty, preserves the conversation context, and hands the case to a human agent.

🎯 The Problem

Traditional AI support often follows:

Customer
   ↓
AI
   ↓
Answer

The problem is that an AI can generate a convincing response even when the underlying information is incomplete or ambiguous.

This can lead to:

Incorrect resolutions
Hallucinated information
Poor customer experiences
Repeated explanations
Loss of context during human handoff
Low trust in automated support

PRISM takes a different approach.

💡 The PRISM Approach
Customer
   ↓
Voice / Text
   ↓
Understand the problem
   ↓
Gather available evidence
   ↓
Evaluate confidence
   ↓
Can the conclusion be trusted?
       │
   ┌───┴────┐
   │        │
  YES       NO
   │        │
Resolve   Identify
automatically uncertainty
             ↓
          Escalate
             ↓
       Human Agent
             ↓
      Context Preserved

The core principle is:

PRISM would rather escalate an uncertain case than confidently give the wrong answer.

🚀 What PRISM Does

PRISM provides a complete customer-support workflow:

🗣️ Voice Support

Customers can explain their problem naturally using realtime voice.

💬 Text Support

Customers can also interact through text chat.

🌐 Multilingual Support

Customers can select their preferred language before starting a conversation, with support for major Indian languages.

🧠 AI Conversation

PRISM understands the customer's problem and extracts relevant information.

🔎 Evidence & Context

The system structures the information it can verify.

📊 Confidence Evaluation

PRISM evaluates whether the available information is sufficient to make a reliable decision.

🚨 Intelligent Escalation

If PRISM cannot confidently determine the issue, it escalates instead of guessing.

👨‍💼 Agent Dashboard

Human agents receive structured case intelligence and the preserved conversation.

🤝 Human Takeover

Agents can take over the conversation while retaining the existing case context.

📡 How PRISM Utilizes Agora

Agora powers PRISM's realtime communication layer.

Rather than treating voice as simply a speech-to-text input field, PRISM uses Agora to provide the communication infrastructure for a realtime support experience.

                    CUSTOMER
                       │
                       │ 🎙️ Voice
                       ▼
                 ┌───────────┐
                 │   AGORA   │
                 │ Realtime  │
                 │   Layer   │
                 └─────┬─────┘
                       │
                       ▼
                 PRISM VOICE
                  EXPERIENCE
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
        Conversation        Case Context
              │                 │
              └────────┬────────┘
                       ▼
                PRISM AI ENGINE
                       │
                       ▼
              Confidence Engine
                       │
              ┌────────┴────────┐
              │                 │
          Confident          Uncertain
              │                 │
              ▼                 ▼
        Continue AI        Escalate
                              │
                              ▼
                       HUMAN AGENT
Why Agora?

Customer support is inherently conversational.

A customer should be able to say:

"Mera payment kat gaya hai, lekin order confirm nahi hua."

instead of having to convert their problem into a structured form.

Agora provides the realtime communication foundation, while PRISM handles the intelligence around that conversation.

Agora handles
Realtime voice communication
Voice session connectivity
Realtime audio transport
Secure session authentication through temporary tokens
PRISM handles
Conversation understanding
Information extraction
Evidence evaluation
Confidence scoring
Decision making
Escalation
Case creation
Context preservation
Human takeover

Agora handles communication. PRISM handles intelligence and decisions.

🔄 PRISM + Agora Flow
1. Customer starts a voice session
Language Selection
       ↓
Voice Interface
       ↓
Start Voice Session

PRISM requests a temporary Agora token from the backend.

Browser
   │
   │ GET /token
   ▼
FastAPI
   │
   │ Generate temporary token
   ▼
Agora

Sensitive Agora credentials remain on the backend.

2. Agora establishes realtime communication
Customer Browser
       │
       │ Secure realtime connection
       ▼
     Agora
       │
       ▼
PRISM Voice Experience

This provides the low-latency communication layer required for natural voice support.

3. PRISM processes the conversation

For example:

Customer:
"Mera payment kat gaya."

PRISM:
"Please provide your transaction ID."

Customer:
"TX48291."

PRISM can build structured context:

Transaction: TX48291
Amount: ₹1,499
Payment: SUCCESS
Order: NOT_CONFIRMED
4. PRISM evaluates confidence

Agora is responsible for communication.

PRISM is responsible for reasoning and decision-making.

AGORA
Realtime communication
        │
        ▼
PRISM
Conversation + Context
        │
        ▼
Confidence Engine
        │
        ▼
Decision Engine

Agora does not decide whether a case should be escalated.

That decision belongs to PRISM.

🚨 The Core PRISM Feature: Uncertainty-Aware Escalation

Suppose PRISM establishes:

Transaction: TX48291
Amount: ₹1,499
Payment: SUCCESS
Order: NOT_CONFIRMED

But it cannot confidently determine the underlying cause.

Instead of hallucinating:

Verified
✓ Transaction found
✓ Payment successful
✓ Amount verified

Uncertain
⚠ Duplicate charge

PRISM escalates:

Unable to confidently determine the issue. Human assistance required.

🤝 Human Takeover

The support journey becomes:

AI Support
    ↓
Human Assistance Required
    ↓
Agent Takes Over
    ↓
Human Agent Connected

The agent doesn't receive an empty ticket.

They receive the information PRISM has already collected.

CASE: PRISM-1042

Customer Issue:
Payment deducted but order not confirmed

Transaction:
TX48291

Amount:
₹1,499

Payment:
SUCCESS

Order:
NOT_CONFIRMED

Uncertainty:
Duplicate charge

Conversation:
[Preserved]

The goal is to eliminate the classic support experience:

"Can you explain your problem again?"

🌐 Multilingual Voice Experience

PRISM is being designed as a multilingual, voice-first support interface, particularly suited for India's diverse language landscape.

The caller can select their preferred language before starting the conversation.

Currently supported languages include:

English
Hindi
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
Nepali
Sanskrit

The initial PRISM greeting is delivered in the selected language using the browser's native Speech Synthesis API.

Example:

English

"Hello, this is PRISM, your AI support assistant. Please describe your problem, and I'll help you resolve it."

Hindi

"नमस्ते, मैं PRISM हूँ, आपका AI सहायता सहायक। कृपया अपनी समस्या बताइए, मैं उसे हल करने में आपकी मदद करूंगा।"

The greeting is triggered by deliberate user interaction rather than automatically playing when the page loads.

🔐 Agora Security

The browser must never receive sensitive Agora credentials.

Browser receives
Agora App ID
Temporary access token
Channel/session information
Backend retains
Agora App Certificate
Customer secret
Other sensitive credentials
              BACKEND
          ┌──────────────┐
          │ App ID       │
          │ Certificate  │ 🔒
          │ Secrets      │ 🔒
          └──────┬───────┘
                 │
           Generate Token
                 │
                 ▼
              Browser
                 │
                 ▼
               Agora

The Agora App Certificate is therefore never shipped to the frontend.

🧠 Architecture
                    PRISM
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
     Caller UI              Agent Dashboard
          │                       │
     Voice / Text             Case Intel
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
                 FastAPI
                  Backend
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
     Context      Confidence     Decision
      Engine        Engine         Engine
        │             │             │
        └─────────────┼─────────────┘
                      │
                ┌─────┴─────┐
                ▼           ▼
               LLM        Tools
                │           │
                └─────┬─────┘
                      ▼
                 Case Engine
                      │
                      ▼
                 Escalation
                      │
                      ▼
                Human Takeover
🏗️ Technology Stack
Frontend
React
Vite
JavaScript
CSS
Browser Speech Synthesis API
Agora Web SDK
Backend
Python
FastAPI
Deterministic confidence engine
Decision/rule engine
LLM integration
Case management
SSE-based communication where applicable
Realtime Communication
Agora
Deployment
Frontend → Vercel
Backend  → Render
🧩 Separation of Responsibilities
Layer	Responsibility
Agora	Realtime voice communication
PRISM Voice Layer	Voice/session interaction
LLM	Conversation understanding and extraction
Confidence Engine	Determines trustworthiness of available evidence
Decision Engine	Determines the next action
Case Engine	Creates and maintains support cases
Agent Dashboard	Presents structured case intelligence
Human Agent	Resolves cases PRISM cannot confidently handle

This separation is intentional.

The LLM is not given unrestricted authority over critical escalation decisions.

🔥 Example End-to-End Scenario

A customer says:

"My payment was deducted, but my order wasn't confirmed."

Step 1: Understand
Intent:
Payment / Order Issue
Step 2: Gather evidence
Transaction: TX48291
Amount: ₹1,499
Payment: SUCCESS
Order: NOT_CONFIRMED
Step 3: Evaluate confidence
Payment       ✓ Verified
Transaction   ✓ Verified
Order         ✓ Verified
Root Cause    ⚠ Uncertain
Step 4: Escalate
Unable to confidently determine the issue.

Human assistance required.
Step 5: Agent receives context
CASE: PRISM-1042

Issue:
Payment deducted, order not confirmed

Transaction:
TX48291

Amount:
₹1,499

Payment:
SUCCESS

Order:
NOT_CONFIRMED

Uncertain:
Duplicate charge

Conversation:
[Preserved]
Step 6: Human takeover
HUMAN ASSISTANCE REQUIRED
          ↓
     AGENT TAKES OVER
          ↓
 HUMAN AGENT CONNECTED

The customer remains within the same support journey.

🆚 Traditional AI Support vs PRISM
Traditional AI Support	PRISM
Focuses on generating answers	Focuses on trustworthy decisions
May answer despite uncertainty	Explicitly represents uncertainty
LLM often controls decisions	Deterministic decision layer
Human handoff can lose context	Full context is preserved
Customer may repeat their issue	Agent receives existing conversation
Often English-first	Multilingual voice-first experience
"Answer at all costs"	"Don't guess when uncertain"
Voice can be an add-on	Realtime communication is built around Agora
🔮 What We Are Building Toward

The current MVP demonstrates the complete PRISM architecture using controlled/demo tools.

The long-term vision is to connect PRISM to real enterprise systems.

                    PRISM
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
 Payment Gateway   Order System     CRM
       │              │              │
       └──────────────┼──────────────┘
                      │
                      ▼
                Evidence Layer
                      │
                      ▼
               Confidence Engine
                      │
             ┌────────┴────────┐
             │                 │
        High Confidence    Low Confidence
             │                 │
             ▼                 ▼
       Auto Resolution      Human Agent
                               │
                               ▼
                         Context Preserved

Future versions can incorporate:

Real payment verification
Real order management systems
CRM integration
Customer history
Knowledge bases
Shipping systems
Evidence correlation
Persistent case storage
Escalation analytics
More advanced confidence modeling
Expanded multilingual conversational support
Agent-assist recommendations
🛣️ Roadmap
                    CURRENT MVP
                         │
          ┌──────────────┴──────────────┐
          │                             │
     Voice + Text                Agent Dashboard
          │                             │
     Multilingual                  Case Intel
          │                             │
          └──────────────┬──────────────┘
                         │
                    Escalation
                         │
                    Takeover
                         │
                         ▼
                 ─────────────────
                    NEXT PHASE
                 ─────────────────
                         │
                    Real APIs
                         │
                 Persistent Cases
                         │
                 Evidence Graph
                         │
                 Advanced Confidence
                         │
                         ▼
                 ─────────────────
                  LONG-TERM VISION
                 ─────────────────
                         │
                  Enterprise AI
                   Support Layer
☁️ Deployment

PRISM is designed to run as two separately deployed applications:

                    INTERNET
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
          VERCEL              RENDER
       React + Vite          FastAPI
             │                   │
             └────── HTTPS ──────┘
                                 │
                       ┌─────────┴─────────┐
                       │                   │
                       ▼                   ▼
                      LLM                Agora
Frontend

Platform: Vercel

Root Directory: frontend
Build Command: npm run build
Output Directory: dist

Environment variable:

VITE_API_URL=https://YOUR-RENDER-BACKEND.onrender.com
Backend

Platform: Render

Typical configuration:

Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

Backend environment variables:

PORT=8001

FRONTEND_URL=https://YOUR-VERCEL-APP.vercel.app
BACKEND_PUBLIC_URL=https://YOUR-RENDER-BACKEND.onrender.com

LLM_API_KEY=...
LLM_BASE_URL=...
LLM_MODEL=...

AGORA_APP_ID=...
AGORA_APP_CERTIFICATE=...
AGORA_CUSTOMER_ID=...
AGORA_CUSTOMER_SECRET=...

Secrets should only exist in the deployment environment and must never be committed to Git.

❤️ Reliability & Fallbacks

PRISM is designed for hackathon/demo environments where external services may occasionally fail.

If the LLM is unavailable because of:

Missing API key
Invalid credentials
Network failure
Provider failure
Model failure
Malformed response
Timeout

PRISM can fall back to its deterministic support path where applicable.

The customer should never receive:

LLM Error
No API key
Internal exception
Traceback
Provider credentials

Instead, the system continues through the available fallback behavior.

💓 Render Keep-Alive

For demo environments using a plan that may sleep after inactivity, PRISM exposes:

GET /health

Response:

{
  "status": "ok",
  "service": "prism-backend"
}

An external HTTP monitoring service can periodically request:

https://YOUR-RENDER-URL.onrender.com/health

A roughly 5-minute interval can be used for hackathon/demo availability.

PRISM intentionally does not implement a backend self-ping loop.

🔒 Security

PRISM follows a server-side secret architecture.

Sensitive credentials remain on the backend.

The frontend only receives information required for normal operation, such as temporary Agora tokens.

The system also avoids exposing:

API keys
Agora certificates
Customer secrets
Environment variables
Full backend tracebacks
Internal provider errors