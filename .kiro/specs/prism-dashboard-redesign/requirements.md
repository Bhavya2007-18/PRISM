# Requirements Document

## Introduction

PRISM Dashboard Redesign transforms the existing PRISM frontend — currently a standalone voice widget (`/`) and a basic agent dashboard (`/agent`) — into a premium, monochromatic AI Operations SaaS platform. The redesign applies a production-grade enterprise aesthetic (Apple + Linear + Stripe-inspired) across every page and component while preserving 100% of the existing backend contracts, Agora integration, voice/chat functionality, session logic, AI state machine, tool calling, escalation logic, and demo data. The result looks and feels like a real AI infrastructure product, not a hackathon prototype.

No backend endpoints, API shapes, or SDK integrations are modified. The change is purely frontend: layout, visual language, component structure, animation, and information architecture.

---

## Glossary

- **Shell**: The outer application frame consisting of the Sidebar and TopBar, shared by every route.
- **Sidebar**: A collapsible vertical navigation panel on the left; 220–240 px expanded, 64–76 px collapsed, rendered on a dark surface (#111111).
- **TopBar**: The horizontal bar at the top of the main workspace; shows page title, connection status, and global controls.
- **Workspace**: The scrollable main content area to the right of the Sidebar and below the TopBar.
- **VoiceOrb**: A large circular interactive element (~120–160 px) at the center of the Live Session page that reflects the current PRISM state via distinct, monochromatic animations.
- **PRISM_STATE**: One of the ten canonical states defined in `frontend/src/config/prismState.js`: IDLE, CONNECTING, LISTENING, UNDERSTANDING, THINKING, ACTING, SPEAKING, ESCALATING, HUMAN_CONNECTED, ERROR.
- **Transcript_Console**: A flat, console-style live transcript panel showing speaker labels and timestamps without chat bubbles.
- **Intelligence_Panel**: The redesigned ThinkingPanel — a vertical animated execution timeline labeled "PRISM INTELLIGENCE".
- **Case_Intelligence_Panel**: A right-hand panel in the Cases view showing AI state pipeline + structured case data.
- **Escalation_Card**: A major escalation treatment surface (not a toast or banner) shown when a case is escalated.
- **Demo_Mode**: A state where the frontend falls back to DEMO_CASES / DEMO_CONV data when the backend is unreachable.
- **Design_Token**: A CSS custom property (e.g., `--surface-0`, `--text-primary`) defined in `index.css`.
- **ttsManager**: The existing singleton in `frontend/src/lib/tts.js` that manages browser speech synthesis. Must not be replaced.
- **getApiUrl**: The existing utility in `frontend/src/lib/api.js`. Must not be replaced.
- **PRISM_STATE_CONFIG**: The existing configuration object in `frontend/src/config/prismState.js`. Must not be replaced.
- **Agent_Page**: The `/agent` route, now a full SaaS operations dashboard.
- **Caller_Page**: The `/` route, now "Live Session" inside the full SaaS Shell.

---

## Requirements

---

### Requirement 1: Shared Application Shell

**User Story:** As any user of PRISM (caller or agent), I want every page to appear inside a consistent, professional SaaS shell, so that the product feels like a unified platform rather than disconnected pages.

#### Acceptance Criteria

1. THE Shell SHALL render a Sidebar and a TopBar on every route, including the Caller_Page (`/`) and the Agent_Page (`/agent`).
2. THE Sidebar SHALL use a dark surface background of `#111111` and a right border of `1px solid #2A2A2A`.
3. THE Sidebar SHALL display the PRISM logotype at the top in `font-weight: 700`, `font-size: 20px`, `color: #F0F0F0`.
4. THE Sidebar SHALL include primary navigation items: Overview, Live Sessions, Cases, Escalations, Agents, and Analytics.
5. THE Sidebar SHALL include secondary navigation items: Integrations, Settings, and a user profile / status indicator at the bottom.
6. WHEN a navigation item is active, THE Sidebar SHALL apply a background of `#222222` and text color `#F0F0F0` with no accent color.
7. WHEN a navigation item is hovered but not active, THE Sidebar SHALL apply a background of `#1A1A1A` with a transition of 100ms ease.
8. WHERE a navigation item has a pending badge count greater than zero, THE Sidebar SHALL display a small pill badge using `var(--danger)` background on that item.
9. THE Sidebar SHALL support a collapsed state at 64–76 px width showing only icons, and an expanded state at 220–240 px showing icons and labels.
10. WHEN the collapse toggle is activated, THE Sidebar SHALL animate the width transition over 200ms ease.
11. THE TopBar SHALL render the current page title on the left in `font-size: 15px`, `font-weight: 600`.
12. THE TopBar SHALL render global connection status (Agora indicator), notification icon, help icon, and user profile on the right.
13. THE TopBar SHALL use `background: var(--surface-0)` and `border-bottom: 1px solid var(--border)`.
14. THE Shell layout SHALL use CSS Grid: `grid-template-columns: [sidebar-width] 1fr` and `grid-template-rows: [topbar-height] 1fr`.
15. IF the backend is unreachable, THE TopBar connection indicator SHALL display a muted status without blocking navigation.

---

### Requirement 2: Design Token System

**User Story:** As a developer maintaining PRISM, I want a coherent, well-structured design token system in `index.css`, so that every component can reference consistent values and the product can be themed without component-level changes.

#### Acceptance Criteria

1. THE Design_Token system SHALL define a monochromatic light surface scale: `--surface-0: #FFFFFF`, `--surface-1: #F9F9F9`, `--surface-2: #F2F2F2`, `--surface-3: #E8E8E8`, `--surface-4: #DCDCDC`.
2. THE Design_Token system SHALL define a dark surface scale: `--dark-0: #0A0A0A`, `--dark-1: #111111`, `--dark-2: #1A1A1A`, `--dark-3: #222222`, `--dark-4: #2E2E2E`.
3. THE Design_Token system SHALL define text tokens: `--text-primary: #111111`, `--text-secondary: #555555`, `--text-tertiary: #888888`, `--text-muted: #B8B8B8`, `--text-inverse: #FFFFFF`.
4. THE Design_Token system SHALL define border tokens: `--border-subtle: #F0F0F0`, `--border: #E5E5E5`, `--border-strong: #D0D0D0`.
5. THE Design_Token system SHALL define semantic color tokens for ok, warn, and danger states including bg and border variants: `--ok`, `--ok-bg`, `--ok-border`, `--warn`, `--warn-bg`, `--warn-border`, `--danger`, `--danger-bg`, `--danger-border`.
6. THE Design_Token system SHALL define typography tokens: `--font-sans` resolving to Inter or system sans-serif, `--font-mono` resolving to JetBrains Mono or system monospace.
7. THE Design_Token system SHALL define spacing/radius tokens: `--r-sm: 6px`, `--r-md: 10px`, `--r-lg: 14px`, `--r-xl: 20px`, `--r-full: 9999px`.
8. THE Design_Token system SHALL define shadow tokens: `--shadow-xs`, `--shadow-sm`, `--shadow-md`, `--shadow-lg` using low-opacity black values only (no color tints).
9. THE Design_Token system SHALL define transition tokens: `--t-fast: 100ms ease`, `--t-base: 200ms ease`, `--t-slow: 350ms ease`.
10. THE Design_Token system SHALL NOT introduce purple gradients, neon blues, glowing effects, or any non-monochromatic accent beyond the existing ok/warn/danger semantics.
11. THE Design_Token system SHALL remain backward-compatible with all existing class names used in the codebase: `.app-shell`, `.card`, `.btn`, `.metric-card`, `.status-dot`, `.status-pill`, `.progress`, `.transcript`, `.voice-orb`, `.waveform`, `.nav-item`.

---

### Requirement 3: VoiceOrb Component

**User Story:** As a caller on the Live Session page, I want the voice orb to clearly and beautifully communicate exactly what PRISM is doing at every moment, so that I always know whether PRISM is listening, thinking, or responding.

#### Acceptance Criteria

1. THE VoiceOrb SHALL render as a circle with a diameter of 120–160 px on desktop and expand to fill the viewport width on mobile.
2. THE VoiceOrb SHALL implement state-specific animations for all ten PRISM_STATEs using SVG rings, CSS keyframes, or canvas — whichever produces the most premium kinetic result while remaining monochromatic.
3. WHEN the VoiceOrb state is IDLE, THE VoiceOrb SHALL display a static ring with `background: var(--surface-2)` and `border: 1.5px solid var(--border-strong)`.
4. WHEN the VoiceOrb state is LISTENING, THE VoiceOrb SHALL display a soft breathing animation with a waveform ring that expands and contracts on a 3-second cycle.
5. WHEN the VoiceOrb state is UNDERSTANDING, THE VoiceOrb SHALL display a slow circular scan or arc sweep animation indicating active parsing.
6. WHEN the VoiceOrb state is THINKING, THE VoiceOrb SHALL display a slow orbital dot or ring rotation animation indicating reasoning.
7. WHEN the VoiceOrb state is ACTING, THE VoiceOrb SHALL display a precise progress arc animation indicating tool execution.
8. WHEN the VoiceOrb state is SPEAKING, THE VoiceOrb SHALL display a smooth waveform expansion animation synchronized to audio playback.
9. WHEN the VoiceOrb state is ESCALATING, THE VoiceOrb SHALL display a subtle outward pulse using `var(--danger)` tones.
10. WHEN the VoiceOrb state is HUMAN_CONNECTED, THE VoiceOrb SHALL display a steady glow using `var(--ok)` tones.
11. WHEN the VoiceOrb state is CONNECTING, THE VoiceOrb SHALL display a slow opacity fade loop.
12. WHEN the VoiceOrb state is ERROR, THE VoiceOrb SHALL display a static border using `var(--danger)`.
13. ALL VoiceOrb animations SHALL use only monochromatic colors (black, white, and grey) except for the ok/warn/danger semantic state overrides.
14. THE VoiceOrb SHALL display a centered state icon or symbol appropriate to the current PRISM_STATE.
15. WHEN the VoiceOrb is clicked while status is idle, THE VoiceOrb SHALL trigger the connect function, preserving all existing Agora join/publish logic.
16. WHEN the VoiceOrb is clicked while status is connected, THE VoiceOrb SHALL trigger the disconnect function, preserving all existing session stop logic.

---

### Requirement 4: Transcript Console

**User Story:** As a caller or agent watching a live session, I want to read the conversation in a clean, console-style transcript panel without chat bubbles, so that the transcript feels like a professional real-time communication log rather than a casual chat interface.

#### Acceptance Criteria

1. THE Transcript_Console SHALL render conversation turns as flat rows with a speaker label column and message column, using no chat bubble backgrounds.
2. THE Transcript_Console SHALL display speaker labels in `font-size: 10px`, `font-weight: 600`, `letter-spacing: 0.08em`, `text-transform: uppercase`, `color: var(--text-muted)`.
3. WHEN a new message is added, THE Transcript_Console SHALL animate each new row with a combined fade and vertical slide-in over 220ms.
4. THE Transcript_Console SHALL display a timestamp for each message in `font-size: 10px`, `font-family: var(--font-mono)`, `color: var(--text-muted)`.
5. WHEN a partial/live transcript is active (user is speaking), THE Transcript_Console SHALL display the partial text with a blinking cursor indicator to signal that the line is live.
6. THE Transcript_Console SHALL auto-scroll to the latest message, and SHALL stop auto-scrolling WHEN the user manually scrolls up.
7. THE Transcript_Console SHALL distinguish USER turns from PRISM turns through label only, using no color coding beyond `var(--text-muted)` labels vs `var(--text-primary)` message text.
8. IF a system event (escalation, takeover) occurs, THE Transcript_Console SHALL insert a centered system-event row using `background: var(--surface-2)`, `color: var(--text-tertiary)`, `font-size: 11px`.

---

### Requirement 5: Intelligence Panel (PRISM INTELLIGENCE)

**User Story:** As an agent or user watching AI activity, I want to see a premium animated execution timeline showing what PRISM is doing step by step, so that I can trust the system and understand its reasoning at any moment.

#### Acceptance Criteria

1. THE Intelligence_Panel SHALL render a vertical execution timeline labeled "PRISM INTELLIGENCE" in a `t-label` style header.
2. THE Intelligence_Panel SHALL display steps in the following order: User intent detected → Context extracted → Action identified → Verification → Resolution or Escalation.
3. WHEN a step is completed, THE Intelligence_Panel SHALL animate the step's dot indicator from inactive to a filled state over 300ms.
4. WHEN a step is active, THE Intelligence_Panel SHALL show a pulsing dot indicator using `var(--text-primary)` with `box-shadow: 0 0 0 3px rgba(0,0,0,0.07)`.
5. WHEN a step is pending, THE Intelligence_Panel SHALL show a hollow dot indicator using `var(--surface-3)` with `border: 1.5px solid var(--border-strong)`.
6. THE connector line between steps SHALL transition from `var(--border)` to `var(--ok)` as steps complete, with a 300ms ease transition.
7. THE Intelligence_Panel SHALL display intent, language, and confidence data from the `aiState` prop when those fields are present.
8. WHEN confidence is 70% or above, THE Intelligence_Panel confidence display SHALL use `var(--ok)` color; WHEN confidence is 40–69%, SHALL use `var(--warn)`; WHEN confidence is below 40%, SHALL use `var(--danger)`.
9. THE Intelligence_Panel SHALL display verified fields with a `✓` prefix in `var(--ok)` and unverified fields with a `–` prefix in `var(--warn)`.
10. THE Intelligence_Panel SHALL display the current tool name and status in `font-family: var(--font-mono)`, `font-size: 11px` when a tool is running.
11. THE Intelligence_Panel SHALL support a `compact` prop that renders a single-line status bar instead of the full timeline, used inside the Transcript_Console area.
12. THE Intelligence_Panel SHALL NOT expose chain-of-thought reasoning — it SHALL show only high-level safe action states.
13. THE Intelligence_Panel SHALL preserve all existing `voiceState` and `aiState` prop interfaces so that the component remains a drop-in replacement for `ThinkingPanel`.

---

### Requirement 6: Live Session Page (Caller Route `/`)

**User Story:** As a caller using PRISM, I want the voice interface to feel like a premium AI product — calm, professional, and responsive — not a raw microphone widget, so that I feel confident using the service.

#### Acceptance Criteria

1. THE Caller_Page SHALL render inside the full Shell (Sidebar + TopBar) with the page title "Live Session".
2. THE Workspace of the Caller_Page SHALL use a three-column layout on desktop: [left context/nav info] [center: voice orb + transcript] [right: Intelligence Panel + Case Context].
3. THE center column SHALL display the VoiceOrb prominently, centered, with at least 32 px padding above and below.
4. THE center column SHALL display the Transcript_Console below the VoiceOrb, showing the live conversation.
5. THE right panel SHALL display the Intelligence_Panel (PRISM INTELLIGENCE section) and below it a Case Context section.
6. THE Case Context section SHALL display Intent, Transaction ID, Amount, Payment Status, Order Status, Language, and Confidence fields when populated from `aiState`.
7. THE Caller_Page SHALL preserve the language selector, mode toggle (Voice / Text), TTS greeting, demo mode, all Agora join/publish/subscribe logic, and the full `connect`/`disconnect` flow from the existing VoiceInterface component.
8. THE Caller_Page chat mode SHALL preserve the quick phrase pills, `sendChatMessage`, ASR microphone button, `ttsManager`, and the `ThinkingPanel compact` status bar.
9. WHEN the session is escalated, THE Caller_Page SHALL display the Escalation_Card inline below the transcript, not as a toast.
10. THE Caller_Page SHALL provide a link to the Agent_Page dashboard labeled "Agent Dashboard →" in `font-size: 11px`, `color: var(--text-muted)`.
11. ON mobile viewports (< 768 px), THE Caller_Page SHALL display a full-screen VoiceOrb as the primary experience, with Transcript_Console and Case Context accessible via a bottom sheet.
12. WHEN the VoiceOrb state is IDLE on mobile, THE Caller_Page SHALL display a prominent "Connect" call-to-action centered below the orb.

---

### Requirement 7: Overview Page

**User Story:** As an operations manager, I want an at-a-glance overview of system health and recent activity when I open the dashboard, so that I can quickly assess the state of the PRISM platform.

#### Acceptance Criteria

1. THE Overview page SHALL be accessible via the "Overview" Sidebar navigation item at `/agent`.
2. THE Overview page SHALL display a metric row with five metric cards: Active Sessions, Resolved Today, Escalated, Avg Resolution Time, and AI Confidence.
3. EACH metric card SHALL display the primary value in `font-size: 30px`, `font-weight: 700`, `letter-spacing: -0.04em` and a supporting label in `font-size: 11px`, `font-weight: 600`, `letter-spacing: 0.06em`, `text-transform: uppercase`.
4. THE metric card for Active Sessions SHALL derive its value from the count of live cases in `displayCases`.
5. THE metric card for Escalated SHALL use `color: var(--danger)` for the primary value when greater than zero.
6. THE metric card for AI Confidence SHALL compute the average `confidence_display` across all `displayCases`.
7. THE Overview page SHALL display a System Health panel listing Agora, AI Agent, Tools, and Escalation components each with a status dot and "Online" label.
8. THE Overview page SHALL display a Recent Activity panel showing up to five recent cases, each clickable to navigate to that case in the Cases view.
9. IN Demo_Mode, THE Overview page SHALL render the same layout using DEMO_CASES data with a clearly visible "Demo" label on the TopBar.

---

### Requirement 8: Live Cases Page — Three-Column Layout

**User Story:** As a human support agent, I want a three-column cases view showing the case list, live transcript, and case intelligence side by side, so that I can monitor and act on escalated cases efficiently.

#### Acceptance Criteria

1. THE Live Cases page SHALL be accessible via the "Live Sessions" or "Cases" Sidebar navigation item.
2. THE Live Cases page SHALL use a three-column layout: cases list (260 px fixed), live conversation transcript (flexible), case intelligence panel (300 px fixed).
3. THE cases list column SHALL display each case as a card-row with a status dot, case ID in monospace, intent/issue summary, language tags, and confidence percentage.
4. WHEN a case is selected, THE cases list SHALL apply `background: var(--surface-2)` and `border: 1px solid var(--border-strong)` to the active row, with a 120ms transition.
5. THE live conversation transcript column SHALL use the Transcript_Console component showing the selected case's conversation history or DEMO_CONV data in Demo_Mode.
6. WHEN `showToolAction` is true, THE live conversation transcript column SHALL render the AIActionPanel compact below the relevant turn.
7. THE case intelligence panel SHALL display the Intelligence_Panel (live AI state pipeline) and the CasePanel (structured case data) stacked vertically.
8. WHEN the active case is escalated and not taken over, THE live conversation transcript column SHALL show the Escalation_Card in a persistent panel above the agent controls at the bottom.
9. THE agent controls bar at the bottom of the conversation column SHALL include: Take over, Resolve, Escalate, and Add note action buttons.
10. THE Take over button SHALL call `POST /cases/{case_id}/takeover` and, on success, trigger `handleAgentAgoraJoin` preserving all existing Agora join/publish logic.
11. THE Agora audio status bar SHALL show the current connection state, mute/unmute control, and disconnect control when audio is connected.
12. THE Agora audio status bar SHALL use `background: var(--ok-bg)` and `border: 1px solid var(--ok-border)` when connected, and `background: var(--surface-1)` with `border: 1px solid var(--border)` when disconnected.
13. WHEN the active case changes, THE live conversation transcript column SHALL scroll to the most recent message.

---

### Requirement 9: Escalations Page

**User Story:** As a human support agent, I want a dedicated Escalations page showing all escalated cases as premium cards, so that I can quickly identify which cases need human intervention and take action.

#### Acceptance Criteria

1. THE Escalations page SHALL be accessible via the "Escalations" Sidebar navigation item.
2. THE Escalations page SHALL display each escalated case (where `escalated === true`) as an Escalation_Card.
3. EACH Escalation_Card SHALL display: case ID, intent/issue, escalation reason, confidence percentage with a progress bar, verified fields, unverified fields, language tags, and a "Take over conversation" button.
4. WHEN a case has been taken over, THE Escalation_Card SHALL transition its header from `background: var(--danger-bg)` to `background: var(--ok-bg)` and replace the take-over button with a "✓ Human agent connected" indicator over 400ms.
5. THE "Take over conversation" button SHALL call `POST /cases/{case_id}/takeover` and update the card state on success.
6. WHEN no escalated cases exist, THE Escalations page SHALL display an empty state message: "No active escalations" centered with `color: var(--text-muted)`.
7. IN Demo_Mode, THE Escalations page SHALL use DEMO_CASES filtered to `escalated === true`.

---

### Requirement 10: Cases / History Page

**User Story:** As a support team lead, I want a case history page with filter controls, so that I can review past interactions and analyze team performance.

#### Acceptance Criteria

1. THE Cases History page SHALL be accessible via the "Cases" Sidebar navigation item.
2. THE Cases History page SHALL display filter pills at the top: All, Open, AI Resolved, Escalated, Human Active.
3. WHEN a filter pill is selected, THE Cases History page SHALL filter the displayed cases to match the selected status, with a 150ms transition.
4. THE case list SHALL display columns: Case ID, Issue, Intent, Amount, Status, Confidence (progress bar + value), Language, and Created time.
5. THE Status column SHALL use `.status-pill` classes: `status-pill--ok` for resolved, `status-pill--danger` for escalated, `status-pill--warn` for open/live.
6. WHEN a case row is clicked, THE Cases History page SHALL navigate to that case in the Live Cases view.
7. IN Demo_Mode, THE Cases History page SHALL display DEMO_CASES data.

---

### Requirement 11: Analytics and Agents Pages (Stub)

**User Story:** As a product stakeholder, I want stub Analytics and Agents pages with demo data clearly labeled, so that the navigation feels complete and the product vision is legible even before real data sources are connected.

#### Acceptance Criteria

1. THE Analytics page SHALL be accessible via the "Analytics" Sidebar navigation item.
2. THE Analytics page SHALL display a "Demo" label in the TopBar when in Demo_Mode.
3. THE Analytics page SHALL render stub metric charts or summary cards showing derived values from DEMO_CASES (e.g., resolution rate, escalation rate, avg confidence).
4. THE Agents page SHALL be accessible via the "Agents" Sidebar navigation item.
5. THE Agents page SHALL display a stub agent roster with at least two placeholder agent rows showing name, status (Online/Offline), and active case count derived from DEMO_CASES.
6. ALL stub pages SHALL clearly label demo content with a `t-label` badge reading "DEMO DATA" in `color: var(--text-muted)`.

---

### Requirement 12: Escalation Card Component

**User Story:** As a human agent, I want the escalation treatment to feel weighty and premium — not a dismissible notification — so that escalations receive the serious attention they deserve.

#### Acceptance Criteria

1. THE Escalation_Card SHALL be a full-width panel rendered in the appropriate page context, not a floating toast or banner.
2. THE Escalation_Card header SHALL display: a status dot, status label (uppercase), and the case ID in monospace.
3. WHEN the case is not taken over, THE Escalation_Card header SHALL use `background: var(--danger-bg)` and `border-bottom: 1px solid var(--danger-border)`.
4. WHEN the case is taken over, THE Escalation_Card header SHALL transition to `background: var(--surface-1)` over 400ms.
5. THE Escalation_Card body SHALL display a two-column grid: left showing issue, language, verified data, and uncertain data; right showing confidence meter, summary, and escalation reason.
6. THE Escalation_Card confidence meter SHALL use a `.progress` bar with color: `var(--ok)` when ≥ 70%, `var(--warn)` when 40–69%, `var(--danger)` when < 40%.
7. THE Escalation_Card footer SHALL display the "Take over conversation" button aligned to the right using `.btn--primary .btn--sm`.
8. WHEN the "Take over conversation" button is clicked, THE Escalation_Card SHALL display a loading state "Connecting…" and disable the button during the request.
9. AFTER a successful takeover, THE Escalation_Card SHALL display "✓ Human agent connected" in `var(--ok)` in place of the button.
10. THE Escalation_Card SHALL support both a `compact` prop (single summary row + take-over button) and a full layout.
11. THE Escalation_Card SHALL preserve the existing `onTakeOver` callback prop interface.

---

### Requirement 13: Animation and Motion System

**User Story:** As a user of PRISM, I want interface animations to feel purposeful, fast, and premium — like Apple-quality motion design — so that state changes are communicated clearly without visual noise.

#### Acceptance Criteria

1. THE Animation system SHALL use CSS keyframes and transitions exclusively — no JavaScript animation libraries.
2. PAGE transitions (route changes) SHALL animate over 150–300ms using opacity and translateY(4px → 0).
3. PANEL transitions (expanding/collapsing panels, side sheets) SHALL animate over 200–400ms using height, opacity, or transform.
4. MAJOR state transitions (e.g., LISTENING → ESCALATING) SHALL animate over 400–700ms.
5. THE Animation system SHALL define the following named keyframes in `index.css`: `fade-in`, `slide-up`, `pop-in`, `dot-pulse`, `orb-breathe`, `orb-think`, `orb-act`, `orb-speak`, `orb-escalate`, `orb-connecting`.
6. ALL interactive elements (buttons, nav items, cards) SHALL have hover and active states with transitions of no longer than `var(--t-base)` (200ms).
7. THE Animation system SHALL use spring-like cubic-bezier values (e.g., `cubic-bezier(0.34, 1.56, 0.64, 1)`) for pop-in and element entry animations.
8. THE Animation system SHALL NOT produce layout shifts; all animated properties SHALL be limited to `opacity`, `transform`, `box-shadow`, `background`, `color`, and `border-color`.
9. WHEN a new transcript line enters, THE Transcript_Console SHALL animate it with `fade-in` + `slide-up` over 220ms.
10. WHEN the Intelligence_Panel step completes, the dot transition SHALL use an ease-in-out curve over 300ms.

---

### Requirement 14: Mobile Responsiveness

**User Story:** As a caller using PRISM on a mobile device, I want a first-class mobile experience, so that I can use the voice interface comfortably without needing a desktop.

#### Acceptance Criteria

1. AT viewport widths below 768 px, THE Shell SHALL replace the Sidebar with a bottom navigation bar showing icon-only nav items.
2. AT viewport widths below 768 px, THE Caller_Page SHALL display the VoiceOrb as the primary full-width element centered on screen.
3. AT viewport widths below 768 px, THE Intelligence_Panel and Case Context SHALL be accessible via a bottom sheet that slides up from the bottom of the screen.
4. AT viewport widths below 768 px, THE metric cards on the Overview page SHALL stack vertically in a single column.
5. AT viewport widths below 768 px, THE Cases three-column layout SHALL collapse to a single scrollable column with a tab bar for List, Transcript, and Intelligence.
6. THE bottom navigation bar SHALL use `background: var(--dark-1)` consistent with the desktop Sidebar surface.
7. WHEN the bottom sheet is open on mobile, THE backdrop SHALL use `background: rgba(0,0,0,0.4)` with a `200ms` fade.

---

### Requirement 15: Functional Preservation Constraints

**User Story:** As a PRISM developer, I need every existing functional behavior to be preserved exactly across the redesign, so that no user-facing capability regresses during the visual upgrade.

#### Acceptance Criteria

1. THE redesigned frontend SHALL preserve all Agora RTC operations: `AgoraRTC.createClient`, `client.join`, `client.publish`, `client.subscribe`, `client.leave`, and `user-published` / `user-unpublished` event handlers.
2. THE redesigned frontend SHALL preserve the `/session/start` and `/session/stop` API calls with identical request bodies and response handling.
3. THE redesigned frontend SHALL preserve the voice state polling loop against `/state/{channel}` at 1500ms intervals and the agent state polling against `/active-state` at 2000ms intervals.
4. THE redesigned frontend SHALL preserve all `ttsManager` calls: `ttsManager.speak` for greetings, `ttsManager.cancel` on disconnect, and the `onStart` / `onEnd` / `onError` callbacks setting `prismSpeaking` state.
5. THE redesigned frontend SHALL preserve the text chat flow: `sendChatMessage`, `POST /chat`, demo reply fallback via `getDemoReply`, and the ASR mic recording flow via `POST /asr`.
6. THE redesigned frontend SHALL preserve escalation detection: reading `d.escalated`, `d.case_id`, and `d.taken_over` from the state polling response and triggering `setEscalated`, `setEscalatedCaseId`, `setTakenOver`.
7. THE redesigned frontend SHALL preserve all DEMO_CASES data, DEMO_CONV sequences, and the `demoMode` fallback logic.
8. THE redesigned frontend SHALL NOT replace or modify `getApiUrl`, `PRISM_STATE_CONFIG`, `PRISM_STATES`, or the `LANGUAGES` / `getLanguageConfig` exports.
9. THE redesigned frontend SHALL NOT change any backend API endpoint URL, request method, request schema, or response schema.
10. THE redesigned frontend SHALL NOT change the Agora channel names (`prism-demo`, `prism-text`) or the agent UID constants.
11. IF a redesigned component replaces an existing component, THE new component SHALL accept the same props with the same names and types as the component it replaces.
12. THE redesigned frontend SHALL pass all existing PRISM_STATE values through to the VoiceOrb CSS class mapping using the pattern `voice-orb--{state.toLowerCase()}`.

---

### Requirement 16: Neumorphic Surface Depth

**User Story:** As a user, I want surfaces to have subtle, tactile depth that feels premium and modern, so that the interface has material quality without excessive decoration.

#### Acceptance Criteria

1. THE surface system SHALL apply very subtle neumorphic shadows to raised interactive elements: `box-shadow: 0 4px 16px rgba(0,0,0,0.06), -2px -2px 8px rgba(255,255,255,0.8)`.
2. THE neumorphic treatment SHALL apply only to interactive surface elements (cards, orb, input fields) — NOT to navigation items, text labels, or data tables.
3. THE neumorphic shadows SHALL use maximum `rgba(0,0,0,0.08)` opacity to remain subtle and not compete with content.
4. THE VoiceOrb idle state SHALL use the neumorphic outset shadow defined in `--neu-out`.
5. THE neumorphic treatment SHALL be defined as a CSS variable `--neu-out` in the Design_Token system.

---

### Requirement 17: Typography Hierarchy

**User Story:** As a user reading the PRISM dashboard, I want clear, intentional typographic hierarchy, so that I can immediately understand which information is most important on any page.

#### Acceptance Criteria

1. THE typographic system SHALL use Inter as the primary sans-serif font, falling back to system-ui.
2. PAGE headings SHALL use `font-size: 28–36px`, `font-weight: 700`, `letter-spacing: -0.04em`.
3. SECTION headings SHALL use `font-size: 15–18px`, `font-weight: 600`, `letter-spacing: -0.01em`.
4. BODY text SHALL use `font-size: 14–15px`, `font-weight: 400`, `line-height: 1.5–1.6`.
5. LABEL / metadata text SHALL use `font-size: 10–11px`, `font-weight: 600`, `letter-spacing: 0.06–0.08em`, `text-transform: uppercase` via the `.t-label` class.
6. MONOSPACE values (case IDs, transaction IDs, timestamps, tool names) SHALL use `font-family: var(--font-mono)`.
7. THE typographic system SHALL NOT use more than four distinct font sizes on any single page.
