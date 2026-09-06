PHASE 0: Lock the Architecture
Priority: 🔴 P0

Before adding features, clean up the foundation enough that we don't build the rest of PRISM on contradictory plumbing.

The audit identified several architectural inconsistencies: the live LLM controls escalation while the documented architecture says the deterministic layer controls it, the frontend stack differs from the documented stack, there are duplicate prompts, and some API contracts have drifted.

0.1 Define the canonical PRISM pipeline

Lock this:

USER
 │
 ▼
INPUT LAYER
 │
 │ microphone / text
 ▼
VOICE LAYER
 │
 ├── VAD
 ├── Turn Detection
 ├── STT / ASR
 ├── Partial Transcript
 └── Language Detection
 │
 ▼
INTELLIGENCE LAYER
 │
 ├── Conversation Context
 ├── Intent
 ├── Entity Extraction
 ├── Memory Retrieval
 ├── Search
 ├── LLM
 ├── Planning
 └── Confidence
 │
 ▼
DECISION / POLICY LAYER
 │
 ├── Is action allowed?
 ├── Is confidence sufficient?
 ├── Does verification exist?
 └── Escalate?
 │
 ▼
ACTION LAYER
 │
 ├── Internal Tools
 ├── APIs
 ├── External Actions
 ├── Communication
 └── Human Escalation
 │
 ▼
VERIFICATION
 │
 ▼
OUTPUT LAYER
 │
 ├── Response Generation
 ├── TTS
 └── Audio Stream
 │
 ▼
USER

This becomes the canonical architecture.

0.2 Define the state machine

Create one shared state enum:

IDLE
CONNECTING
LISTENING
UNDERSTANDING
THINKING
PLANNING
ACTING
VERIFYING
SPEAKING
ESCALATING
HUMAN_CONNECTED
RESOLVED
FAILED
ENDED

The audit specifically identifies the current state handling as ad hoc and inconsistent between frontend/backend.

Eventually:

backend
   ↓
PrismState
   ↓
event
   ↓
frontend
   ↓
animation

One state machine.

One source of truth.

0.3 Decide the LLM/policy relationship

This is very important.

Don't choose:

LLM → directly decides everything

and don't make the LLM useless:

LLM → just generates sentences

Use:

LLM
 ↓
PROPOSES
 ↓
POLICY / DECISION ENGINE
 ↓
APPROVES / REJECTS / MODIFIES
 ↓
TOOL

So:

LLM provides intelligence. Policy provides control. Agora provides realtime communication. Humans provide the safety net.

This resolves the exact contradiction identified in the audit.

PHASE 1: THE VOICE AI CORE
🔥 THIS IS YOUR FIRST MAJOR BUILD

Everything else waits.

The goal isn't:

"We have an AI voice demo."

The goal is:

PRISM can conduct a complete realtime voice conversation reliably.

1.1 Agora realtime foundation

Make Agora the actual communication fabric.

Build
Agora RTC connection
temporary token generation
user UID
AI UID
agent UID
channel lifecycle
join
leave
reconnect
connection state
network state
mute/unmute
audio publishing
audio subscription
interruption handling
session start
session stop

Current Agora integration is already functional, including Conversational AI v2 and human takeover.

Now make it production reliable.

Done when
Start call
   ↓
Agora connects
   ↓
AI joins
   ↓
User speaks
   ↓
AI hears
   ↓
AI responds
   ↓
User interrupts
   ↓
AI stops speaking
   ↓
AI listens again

No page refresh.

No demo mode.

No manual hacks.

1.2 Input layer

Your diagram says:

Capture Audio → VAD → Turn Detection

Implement this properly.

Components
Microphone
   ↓
Audio Capture
   ↓
VAD
   ↓
Speech Start
   ↓
Speech Frames
   ↓
Speech End
   ↓
Turn Complete

Need:

voice activity detection
silence threshold
minimum speech duration
maximum utterance duration
noise handling
interruption
barge-in
turn timeout
endpoint detection

Current backend already has Silero VAD and Faster Whisper, but this needs to become part of a reliable real voice path rather than an auxiliary capability.

1.3 Real realtime STT

This is one of the biggest current gaps.

The audit says real voice transcripts are not currently surfaced to the UI, with live transcript functioning only in demo mode.

Build:

Audio
 ↓
Agora / STT
 ↓
Partial transcript
 ↓
Final transcript
 ↓
Conversation event

Example:

Listening...

"bhai mera..."
       ↓
"bhai mera payment..."
       ↓
"bhai mera payment kat gaya..."
       ↓
FINAL

Frontend receives every meaningful transcript event.

1.4 Language detection

Start with:

English
Hindi
Hinglish

Not 23 languages yet.

The audit confirms that the current configuration only defines English and Hindi despite the broader 22-language UI claim.

Build the architecture so languages can later be plugged in:

Language Adapter
 ├── hi-IN
 ├── en-IN
 ├── Hinglish
 ├── ta-IN
 ├── bn-IN
 └── ...

But don't waste P0 time implementing 23 languages.

1.5 Conversation engine

Build a real conversational loop:

USER SPEAKS
    ↓
TRANSCRIPT
    ↓
CONTEXT UPDATE
    ↓
INTENT
    ↓
MISSING INFORMATION?
    │
 ┌──┴──┐
 YES   NO
 │      │
 ▼      ▼
ASK    PLAN
       │
       ▼
      ACT

It needs to handle:

Example

User:

"Bhai payment kat gaya."

PRISM:

"I can check that. What was the transaction amount?"

User:

"1499."

PRISM:

intent = payment_issue
amount = 1499
transaction_id = unknown

Then:

"Do you have the transaction ID?"

This is much more important than making the LLM sound clever.

1.6 Barge-in / interruption

This should be treated as a first-class feature.

Example:

PRISM:

"I found your transaction and..."

User:

"Haan but..."

PRISM immediately stops speaking.

TTS
 ↓
INTERRUPTED
 ↓
STOP AUDIO
 ↓
LISTENING

This is what makes the system feel genuinely realtime rather than a walkie-talkie with a language model taped onto it.

1.7 LLM intelligence

Create a clean agent runtime.

AgentRuntime
│
├── ContextManager
├── IntentEngine
├── MemoryManager
├── Planner
├── ToolRouter
├── PolicyEngine
├── ConfidenceEngine
└── ResponseGenerator

Remove the confusing current "Pipecat" naming because the audit confirms it isn't actually using Pipecat.

1.8 Planning

Your handwritten Think → Plan → Act should become real.

Example:

{
  "goal": "resolve_payment_issue",
  "steps": [
    "identify_transaction",
    "check_transaction",
    "verify_result",
    "determine_resolution"
  ]
}

Then:

PLAN
 ↓
STEP 1
 ↓
STEP 2
 ↓
STEP 3

The UI only exposes safe high-level states, not hidden chain-of-thought.

1.9 Tool calling

Build a proper tool registry.

TOOLS
│
├── check_transaction
├── get_order
├── refund_status
├── verify_identity
├── search_knowledge
├── create_case
├── escalate
└── notify_human

Each tool should have:

name
description
input schema
output schema
permissions
timeout
retry policy
verification requirement
audit logging
1.10 Tool execution safety

Never:

LLM → API

Instead:

LLM
 ↓
Tool Request
 ↓
Schema Validation
 ↓
Policy Check
 ↓
Permission Check
 ↓
Tool
 ↓
Result Validation
 ↓
Verification
 ↓
LLM

This becomes crucial once you allow real external actions.

1.11 Confidence engine

Current confidence is label-based rather than genuinely numeric.

Build:

intent confidence
entity confidence
tool confidence
resolution confidence
overall confidence

Example:

Intent           97%
Transaction      94%
Tool result      99%
Resolution       61%

Overall           72%

Then define policy:

> 85%
AI can resolve

60–85%
AI may continue gathering information

< 60%
consider escalation

critical action
always require verification
1.12 Verification

Never allow:

Tool result → immediately tell user "done"

Instead:

ACTION
 ↓
RESULT
 ↓
VERIFY
 ↓
CONFIRM
 ↓
RESPOND

For payment:

check_transaction
       ↓
transaction found?
       ↓
status verified?
       ↓
order status checked?
       ↓
resolution valid?
       ↓
speak
1.13 TTS/output layer

Build:

Response
 ↓
Sentence segmentation
 ↓
TTS
 ↓
Audio stream
 ↓
Agora
 ↓
User

Requirements:

low latency
streaming TTS if available
interruption
cancellation
language-specific voice
natural pauses
sentence-level streaming
no duplicate speech
recovery from TTS failure
1.14 Voice failure recovery

Every failure gets a recovery path.

STT FAILURE
→ ask user to repeat

LLM FAILURE
→ fallback response

TOOL FAILURE
→ retry → alternative → escalate

TTS FAILURE
→ text fallback

AGORA FAILURE
→ reconnect

NETWORK FAILURE
→ reconnect state

UNKNOWN STATE
→ safe reset
1.15 VOICE PHASE DEFINITION OF DONE

Do not leave Phase 1 until this works:

                    USER
                      │
                    SPEAK
                      ↓
                 ┌─────────┐
                 │ LISTEN  │
                 └────┬────┘
                      ↓
                LIVE TRANSCRIPT
                      ↓
                 UNDERSTAND
                      ↓
                  THINK
                      ↓
                   PLAN
                      ↓
                   ACT
                      ↓
                VERIFY RESULT
                      ↓
                 RESPOND
                      ↓
                  TTS/AUDIO
                      ↓
                   SPEAK
                      ↓
                USER INTERRUPTS
                      ↓
                  LISTEN AGAIN

Real voice.

Real transcript.

Real tool call.

Real response.

Real interruption.

No demo-mode dependency.

That is your first finish line.

PHASE 2: SECURITY + PRODUCTION DEPLOYMENT
🔐 Your second priority

Once voice is solid, lock the doors.

The current secret architecture is already good in principle: sensitive Agora/LLM credentials remain server-side while the browser receives the App ID and temporary token.

Now make it production-grade.

2.1 Authentication

Implement:

User
 ↓
Login
 ↓
Session
 ↓
Access Token
 ↓
API

Options:

Clerk
Auth0
Supabase Auth
custom JWT

For speed, use a managed auth provider.

2.2 Authorization

Roles:

OWNER
ADMIN
AGENT
SUPERVISOR
USER

Permissions:

USER
→ own conversations

AGENT
→ assigned cases

SUPERVISOR
→ all cases

ADMIN
→ configuration

OWNER
→ everything
2.3 API security

Implement:

CORS restrictions
rate limiting
request validation
body limits
authentication middleware
authorization middleware
API versioning
timeout policies
replay protection where needed
2.4 Secret management

No secrets in:

frontend
Git
logs
client bundles
error messages
database plaintext

Secrets:

Agora App Certificate
LLM API Keys
Database URL
Auth Secret
TTS credentials
Search API keys

Use Render/Vercel environment secrets.

Rotate keys.

2.5 Data protection

Sensitive conversation data needs:

encryption in transit
encryption at rest
access controls
retention policy
deletion policy
audit logs
2.6 Database

Move:

in-memory CaseState

to:

PostgreSQL

The current in-memory architecture is allowed for MVP, but it isn't what you want for a fully persistent product.

Core tables:

users
organizations
agents

sessions
messages
transcripts

cases
transactions
tool_executions

escalations
handoffs

memories
documents

audit_logs
events
2.7 Redis

Add Redis for:

session state
locks
rate limits
short-term context
queues
realtime events
caching

Don't make Redis the permanent source of truth.

Postgres = durable truth.

Redis = speed layer.

2.8 Observability

Implement:

logs
metrics
traces
errors

Track:

voice latency
STT latency
LLM latency
tool latency
TTS latency
total response latency
Agora connection failures
tool failures
escalations
resolution rate

Add Sentry.

The audit currently marks monitoring as absent, although optional in the MVP spec.

2.9 Deployment
Frontend
GitHub
 ↓
Vercel
 ↓
Production
Backend
GitHub
 ↓
Render
 ↓
FastAPI

Then:

Production
Staging
Development

Three environments.

2.10 Fix deployment issues

Before production:

fix docker-compose
add/fix Dockerfiles
fix backend requirements
fix import paths
normalize ports
validate Render startup
health endpoint
readiness endpoint
graceful shutdown

The audit specifically identifies the broken Docker Compose, incomplete backend requirements and possible Render import-path issue.

PHASE 3: MEMORY + CONTEXT + SEARCH

Now PRISM stops being a clever call and becomes an agent.

3.1 Short-term memory

During a call:

conversation
current intent
entities
tool results
current plan
current state
3.2 Long-term memory

Store useful information:

previous cases
preferences
past interactions
resolved issues
user-provided facts

But memory needs controls.

remember
forget
delete
expiration
privacy
3.3 Context engine

Create:

ContextManager

with:

conversation context
case context
user context
tool context
environment context
memory context

Then construct:

LLM Context
=
Current Turn
+
Conversation
+
Case
+
Relevant Memory
+
Retrieved Knowledge
+
Tool Results
+
Policy
3.4 Search

Add retrieval.

USER QUESTION
 ↓
SEARCH
 ↓
RELEVANT DOCUMENTS
 ↓
RANK
 ↓
CONTEXT
 ↓
LLM

Use this for:

FAQs
support policies
product documentation
refund policies
internal knowledge
3.5 RAG

Eventually:

Documents
 ↓
Chunk
 ↓
Embedding
 ↓
Vector DB
 ↓
Semantic Search
 ↓
Reranking
 ↓
LLM

Potential stack:

Postgres
+
pgvector

Keep it simple.

PHASE 4: FULL ACTION ENGINE

Now we expand beyond the mock transaction.

Your handwritten diagram explicitly has:

Tools → API → Memory → Search → Communication Control → External Action

So we should actually implement each.

4.1 Tool framework

Create a universal:

ToolRegistry

Every tool follows:

request
→ validate
→ authorize
→ execute
→ verify
→ log
→ return
4.2 Internal tools

Examples:

check_transaction()
get_order()
get_customer()
create_case()
update_case()
search_knowledge()
4.3 External APIs

Build adapters:

PaymentProvider
OrderProvider
CRM
Email
SMS
Calendar
Database

Architecture:

PRISM
  ↓
Adapter
  ↓
External API

Never let the agent know provider-specific implementation details.

4.4 External actions

Eventually PRISM can do:

refund payment
cancel order
reschedule delivery
send email
send SMS
create support ticket
update CRM
book appointment

But dangerous actions require policy.

Example:

REFUND ₹1,499

LLM proposes
      ↓
Policy validates
      ↓
Permission check
      ↓
User confirmation if required
      ↓
Execute
      ↓
Verify
      ↓
Audit
PHASE 5: HUMAN SUPPORT SYSTEM

The current dashboard/takeover already works, so now make it a real system.

5.1 Case management

Case lifecycle:

NEW
 ↓
AI_HANDLING
 ↓
WAITING
 ↓
ESCALATED
 ↓
HUMAN_ACTIVE
 ↓
RESOLVED
 ↓
CLOSED
5.2 Human handoff

Your killer flow:

AI
 ↓
confidence drops
 ↓
policy says escalate
 ↓
case created
 ↓
context packaged
 ↓
agent notified
 ↓
agent joins Agora
 ↓
AI hands over
 ↓
HUMAN_CONNECTED
5.3 Context transfer

Agent receives:

User intent
Conversation
Transcript
Language
Transaction
Tool results
Actions taken
Confidence
Reason for escalation
Recommended next action

The user should never have to repeat the story.

5.4 Agent controls

Agent:

Take over
Mute
Speak
Resolve
Escalate
Add note
Transfer
End session
5.5 Dynamic session tracking

Fix the current hard-coded dashboard channel issue.

The audit specifically found that Agent currently polls prism-text even for voice sessions.

Instead:

Session
 ↓
session_id
 ↓
channel_name
 ↓
agent dashboard

No hardcoded channels.

PHASE 6: MULTI-MODAL PRISM

After voice is excellent:

VOICE
TEXT
IMAGE
DOCUMENT

Potential flow:

User uploads screenshot
       ↓
Vision
       ↓
Extract information
       ↓
Context
       ↓
Agent

For example:

"Payment failed"

screenshot of payment screen.

PRISM reads it.

PHASE 7: MULTI-LANGUAGE

Now expand beyond:

English
Hindi
Hinglish

Architecture:

Language
 ↓
ASR
 ↓
Intent
 ↓
LLM
 ↓
Response
 ↓
TTS

Eventually:

English
Hindi
Hinglish
Bengali
Tamil
Telugu
Marathi
Gujarati
Kannada
Malayalam
Punjabi
...

But only after the core language pipeline is rock solid.

PHASE 8: ANALYTICS

Build the operations layer.

Dashboard:

Total Sessions
AI Resolution Rate
Human Escalation Rate
Average Resolution Time
Average AI Confidence
Tool Success Rate
Voice Latency
Customer Satisfaction

Charts:

sessions/day
resolution/day
escalation/day
language distribution
intent distribution
agent performance
PHASE 9: TESTING

This is where "it works on my machine" goes to the graveyard.

The audit currently only has backend pytest coverage, with frontend testing incomplete.

Build:

Unit tests
context
confidence
policy
tools
state machine
language detection
Integration tests
voice → STT
STT → LLM
LLM → tool
tool → verification
escalation → case
E2E tests
user starts session
 ↓
speaks
 ↓
AI responds
 ↓
tool executes
 ↓
resolution
Failure tests
Agora unavailable
STT unavailable
LLM unavailable
TTS unavailable
tool timeout
network disconnect
invalid transaction
low confidence
PHASE 10: FRONTEND REDESIGN

Only now I'd spend serious time on the beautiful UI you've been designing.

The audit says the current frontend is Vite + React + JS with inline styles rather than the previously documented Next.js/TS/Tailwind/shadcn/Framer stack.

I would not make a framework migration the priority right now.

Instead:

Current working React/Vite
          ↓
Design system
          ↓
New components
          ↓
New motion
          ↓
New realtime visualization

Then decide later whether migration is worth it.

Implement your visual system:
Monochrome
+
Editorial typography
+
Clean SaaS structure
+
Tactile 3D
+
Apple motion
+
Subtle neumorphism

And especially:

PRISM Core
LISTENING
     ↓
UNDERSTANDING
     ↓
THINKING
     ↓
PLANNING
     ↓
ACTING
     ↓
VERIFYING
     ↓
SPEAKING

The animation isn't decoration.

The animation is the visual representation of the agent's state.

PHASE 11: MOBILE

Once desktop is stable:

React web
 ↓
Responsive
 ↓
PWA / Mobile

Mobile becomes voice-first:

        PRISM

          ◉

     LISTENING

"bhai mera payment..."

──────────────────

Current action
Checking transaction

──────────────────

        ↑
    swipe context
PHASE 12: PRODUCTION HARDENING

Final pass.

Reliability
retries
circuit breakers
fallbacks
timeouts
graceful degradation
reconnection
queue recovery
Security
penetration testing
dependency scanning
secret scanning
RBAC testing
API abuse testing
audit verification
Performance

Measure:

Mic → STT
STT → LLM
LLM → Tool
Tool → Result
Result → TTS
TTS → User

Then optimize each bottleneck.

The actual build order I recommend

If we're building this together, this is the order I would literally execute the tickets:

╔══════════════════════════════════════════╗
║              P0: VOICE CORE              ║
╚══════════════════════════════════════════╝

01  Clean agent architecture
02  Canonical PrismState
03  Agora session lifecycle
04  Realtime audio pipeline
05  VAD + turn detection
06  Real Agora transcript events
07  Partial transcript UI
08  Final transcript pipeline
09  Conversation context engine
10  Intent extraction
11  Missing information engine
12  LLM planning
13  Tool registry
14  Tool schema validation
15  Policy / deterministic gate
16  Transaction tool
17  Verification engine
18  Numeric confidence
19  Response generation
20  Streaming TTS
21  Barge-in
22  Interruption handling
23  Voice error recovery
24  End-to-end voice test

              ↓

╔══════════════════════════════════════════╗
║        P1: SECURITY + DEPLOYMENT         ║
╚══════════════════════════════════════════╝

25  Authentication
26  Authorization / RBAC
27  API security
28  Rate limiting
29  Secret management
30  Database
31  Redis
32  Audit logging
33  Error monitoring
34  Metrics
35  Tracing
36  Staging environment
37  Production environment
38  Docker
39  Render hardening
40  Vercel hardening
41  Health / readiness
42  Backup / recovery

              ↓

╔══════════════════════════════════════════╗
║       P2: MEMORY + KNOWLEDGE             ║
╚══════════════════════════════════════════╝

43  Short-term memory
44  Long-term memory
45  Memory retrieval
46  Memory permissions
47  Knowledge base
48  Document ingestion
49  Embeddings
50  Vector search
51  RAG
52  Search / retrieval pipeline

              ↓

╔══════════════════════════════════════════╗
║          P3: ACTION PLATFORM             ║
╚══════════════════════════════════════════╝

53  Tool registry
54  API adapters
55  External actions
56  Communication tools
57  Email
58  SMS
59  CRM
60  Payment actions
61  Action permissions
62  Confirmation policies
63  Verification
64  Rollback / compensation
65  Tool audit trail

              ↓

╔══════════════════════════════════════════╗
║         P4: HUMAN OPERATIONS             ║
╚══════════════════════════════════════════╝

66  Case management
67  Agent management
68  Dynamic channels
69  Agent presence
70  Queue
71  Assignment
72  Human takeover
73  Context transfer
74  Agent notes
75  Transfer between agents
76  Supervisor view
77  Case resolution

              ↓

╔══════════════════════════════════════════╗
║          P5: PRODUCT COMPLETION          ║
╚══════════════════════════════════════════╝

78  Analytics
79  Advanced languages
80  Multimodal input
81  Image understanding
82  Document understanding
83  Customer feedback
84  CSAT
85  Notifications
86  Billing / plans
87  Organization workspaces
88  API access
89  Webhooks
90  Developer platform

              ↓

╔══════════════════════════════════════════╗
║             P6: UI / UX                  ║
╚══════════════════════════════════════════╝

91  New design system
92  Typography system
93  Monochrome theme
94  PRISM Core
95  Realtime animations
96  Physical cards
97  AI state visualization
98  Agent workspace
99  Case workspace
100 Mobile experience
101 Accessibility
102 Performance polish
The most important architectural distinction

I would divide the whole product into 7 actual engines:

                  ┌─────────────────┐
                  │    PRISM CORE   │
                  └────────┬────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ↓                   ↓                   ↓

 ┌───────────┐       ┌────────────┐      ┌───────────┐
 │   VOICE   │       │INTELLIGENCE│      │   ACTION  │
 │   ENGINE  │       │   ENGINE   │      │   ENGINE  │
 └─────┬─────┘       └──────┬─────┘      └─────┬─────┘
       │                    │                   │
       │                    │                   │
       ↓                    ↓                   ↓
    Agora               LLM/Memory          Tools/APIs
    STT/TTS             Search/Context       External Actions
    VAD                 Planning             Verification

       └───────────────────┼───────────────────┘
                           ↓
                   ┌──────────────┐
                   │ POLICY ENGINE│
                   └──────┬───────┘
                          ↓
                ┌────────────────────┐
                │ HUMAN SUPPORT      │
                │ ENGINE             │
                └─────────┬──────────┘
                          ↓
                   Agent / Case / Agora

                          +
                          
                ┌────────────────────┐
                │ PLATFORM ENGINE    │
                │ Auth / DB / Redis  │
                │ Security / Logs    │
                └────────────────────┘

That is the PRISM I would build.

What "100% functional PRISM" means

When we're actually done, this should work:

User

"Bhai mera payment kat gaya but order confirm nahi hua."

PRISM
LISTENING
   ↓
UNDERSTANDING
   ↓
Intent: Payment Issue
   ↓
Missing transaction information
   ↓
ASK

User gives ID.

THINKING
   ↓
PLANNING
   ↓
CHECK TRANSACTION
   ↓
TOOL EXECUTION
   ↓
RESULT
   ↓
VERIFY
   ↓
CONFIDENCE = 94%
   ↓
RESOLVE
   ↓
GENERATE RESPONSE
   ↓
TTS
   ↓
SPEAK

If confidence is low:

CONFIDENCE = 48%
       ↓
POLICY
       ↓
ESCALATE
       ↓
CREATE CASE
       ↓
TRANSFER CONTEXT
       ↓
AGENT NOTIFIED
       ↓
AGENT JOINS AGORA
       ↓
HUMAN_CONNECTED

And the user never needs to restart the story.

That is the real PRISM loop.

One thing I would not do

I would not spend the next week migrating Vite → Next.js just because the old tech-stack document says so.

The audit shows that the current Vite/React frontend is already functional, while the genuinely important gaps are real voice transcript integration, state consistency, architecture reconciliation, deployment correctness and security.

So the order should be:

Make PRISM think and talk flawlessly → make it safe → make it production-ready → give it memory/actions/humans → then make it gorgeous.

That gives us a much stronger product than polishing a beautiful shell around a half-real voice agent.

The first milestone I would now define

PRISM v0.2: True Realtime Agent

Agora
  ↓
Audio
  ↓
VAD
  ↓
STT
  ↓
Live Transcript
  ↓
Context
  ↓
LLM
  ↓
Plan
  ↓
Policy
  ↓
Tool
  ↓
Verification
  ↓
Response
  ↓
Streaming TTS
  ↓
Agora
  ↓
User

             ↕
         INTERRUPTION

             ↕
       HUMAN TAKEOVER

Everything in that diagram must work with real services, real voice, real events and real failure handling before we call the voice layer finished.