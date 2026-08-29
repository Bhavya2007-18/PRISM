# PRISM

### Polyglot Real-time Intelligent Support Mediator

> **One conversation. Any language. The right resolution.**

PRISM is a real-time, multilingual conversational AI agent designed to act as the first point of contact between people and support systems.

It understands natural, multilingual and code-switched conversations, extracts the information needed to resolve a request, interacts with external tools, maintains conversation context, and intelligently escalates cases to human agents when confidence is too low or human intervention is required.

Built for the **EchoSphere: Agora Conversational AI Hackathon**.

---

## 🌐 The Problem

Traditional assistance systems assume that users will:

- Speak a specific language
- Follow a predefined conversation flow
- Clearly describe their problem
- Provide information in the expected format
- Repeat themselves when transferred to a human

Real conversations don't work like that.

A caller may switch between Hindi and English, speak with background noise, interrupt the agent, forget important details, or describe a problem in an unexpected way.

Most voice bots respond by either:

> misunderstanding the user, repeatedly asking questions, or confidently giving the wrong answer.

PRISM takes a different approach.

---

# 💡 Our Approach

PRISM acts as a **universal conversational layer** between people, AI-powered services, and human agents.

```text
                    👤 CALLER
                       │
             Any language / accent
             Natural or messy speech
                       │
                       ▼
              ┌─────────────────┐
              │      AGORA      │
              │ Real-Time Voice │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │      PRISM      │
              │ Conversation AI │
              └────────┬────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Understand     Reason       Remember
          │            │            │
          └────────────┼────────────┘
                       ▼
                Decision Engine
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Resolve      Call Tools   Escalate
          │            │            │
          ▼            ▼            ▼
        DONE        Take Action   HUMAN
                                    │
                                    ▼
                              Full Context
