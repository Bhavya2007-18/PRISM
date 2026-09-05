# Design Document: PRISM Dashboard Redesign

## Overview

This document describes the technical design for transforming the PRISM frontend from two disconnected pages — a raw voice widget (`/`) and a basic agent dashboard (`/agent`) — into a production-grade AI Operations SaaS platform.

The redesign is **purely frontend**: layout, visual language, component structure, animation, and information architecture. Zero backend endpoints, API shapes, Agora integrations, or SDK contracts are modified. Every functional behavior preserved in `requirements.md §15` is treated as a hard constraint; this design explains exactly how each is preserved.

**Target aesthetic**: monochromatic, enterprise-grade — Apple + Linear + Stripe-inspired. No purple gradients, no glows, no color beyond the ok/warn/danger semantic tokens already established.

---

## Architecture

### High-level structure

```
App.jsx
└── AppShell (sidebar + topbar wrapper — NEW)
    ├── Sidebar.jsx (collapsible, dark surface)
    ├── TopBar.jsx  (page title + global controls)
    └── <Outlet /> / children
        ├── / → Caller.jsx   (Live Session page)
        └── /agent → Agent.jsx (Operations dashboard)
```

`App.jsx` wraps both routes inside `<AppShell>`. Each page renders only its workspace content — no page owns its own shell anymore.

### State ownership

| State | Owner | Passed to |
|---|---|---|
| `sidebarExpanded` | `AppShell` | `Sidebar` |
| `activeNav` (intra-agent tabs) | `Agent.jsx` | sidebar nav item badges |
| `escalationCount` | `Agent.jsx` | `AppShell` → `Sidebar` via prop |
| `voiceState`, `aiState` | `VoiceInterface` internal | `VoiceOrb`, `IntelligencePanel`, `TranscriptConsole` as props |
| `cases`, `demoMode` | `Agent.jsx` | all sub-pages via props |
| TTS, Agora, polling | `VoiceInterface` / `Agent.jsx` | unchanged, no extraction |

AppShell receives a light `sidebarBadges` prop (object of `{ escalations: number }`) from Agent.jsx so it can show badge counts without owning business data.

### Routing

React Router v6 routes stay identical:

```jsx
// App.jsx
<BrowserRouter>
  <Routes>
    <Route element={<AppShell />}>
      <Route path="/"      element={<Caller />} />
      <Route path="/agent" element={<Agent  />} />
    </Route>
  </Routes>
</BrowserRouter>
```

`AppShell` renders `<Outlet />` in the workspace area. The active sidebar nav item for the shell-level links (`/` and `/agent`) is determined by `useLocation().pathname`. Intra-agent tab navigation (`overview`, `cases`, etc.) remains `activeNav` state inside `Agent.jsx`, not the router.

---

## Components and Interfaces

### `AppShell.jsx` (NEW)

**Responsibilities**: shell grid layout, sidebar + topbar rendering, sidebar collapse state.

```jsx
// Props
{
  sidebarBadges?: { escalations?: number },  // badge counts from parent
  pageTitle?: string,                         // override for TopBar
  connectionStatus?: 'ok' | 'warn' | 'offline',
}
```

Internal state:
- `sidebarExpanded: boolean` — controls sidebar width via CSS variable injection on the shell div.

Layout uses `app-shell` CSS Grid class (already in `index.css`):
- `grid-template-columns: var(--sidebar-width) 1fr`
- `grid-template-rows: var(--topbar-height) 1fr`

On collapse toggle, `--sidebar-width` is overridden inline to `72px`. The Sidebar handles its own content visibility at that width.

---

### `Sidebar.jsx` (NEW)

**Responsibilities**: navigation, branding, system status, collapse toggle.

```jsx
// Props
{
  expanded: boolean,
  onToggle: () => void,
  badges?: { escalations?: number },
  activeRoute: string,     // from useLocation
  activeIntraNav?: string, // for /agent sub-tabs
}
```

Navigation items:

```js
const PRIMARY_NAV = [
  { id: 'overview',     label: 'Overview',      icon: '○', route: '/agent', intraNav: 'overview' },
  { id: 'live-sessions',label: 'Live Sessions', icon: '◉', route: '/agent', intraNav: 'cases' },
  { id: 'cases',        label: 'Cases',         icon: '▣', route: '/agent', intraNav: 'history' },
  { id: 'escalations',  label: 'Escalations',   icon: '⚠', route: '/agent', intraNav: 'escalations',
    badgeKey: 'escalations' },
  { id: 'agents',       label: 'Agents',        icon: '◎', route: '/agent', intraNav: 'agents' },
  { id: 'analytics',    label: 'Analytics',     icon: '▦', route: '/agent', intraNav: 'analytics' },
  { id: 'live-session', label: 'Live Session',  icon: '🎙', route: '/' },
]

const SECONDARY_NAV = [
  { id: 'integrations', label: 'Integrations', icon: '⊕' },
  { id: 'settings',     label: 'Settings',     icon: '⊙' },
]
```

When `expanded === false`, only icons render; labels are hidden via `opacity: 0; width: 0; overflow: hidden` with a CSS transition. The branding logotype collapses to "P".

Active item detection:
- For `/` route: `id === 'live-session'` is active.
- For `/agent` route: active item matches `intraNav === activeIntraNav`.

Badge rendering: when `badges[item.badgeKey] > 0`, a `.nav-item__badge` span renders inside the nav item with `var(--danger)` background.

---

### `TopBar.jsx` (NEW)

**Responsibilities**: page title, connection indicator, notification icon, user profile chip.

```jsx
// Props
{
  title: string,
  demoMode?: boolean,
  connectionStatus?: 'ok' | 'warn' | 'offline',
  lastUpdated?: Date | null,
  onToggleSidebar: () => void,
}
```

Layout: `display: flex; align-items: center; padding: 0 24px; gap: 16px`. Left side: page title + optional "Demo" label. Right side: connection indicator, notification icon (static bell, no functionality in v1), user avatar chip.

Connection indicator uses `.status-dot` with `status-dot--ok` / `status-dot--danger` class. When `demoMode` is true, a `t-label` badge reading "DEMO" appears next to the title in `color: var(--text-muted)`.

---

### `VoiceOrb.jsx` (NEW — presentational only)

**Responsibilities**: animated state visualization. Zero business logic. Zero API calls.

```jsx
// Props
{
  state: string,    // one of PRISM_STATES — e.g. 'LISTENING'
  onClick: () => void,
  size?: number,    // diameter in px, default 160
  audioLevel?: number, // 0-1, for waveform amplitude when SPEAKING
}
```

**Rendering structure**:

```
<div class="voice-orb-wrapper" style="width: {size}px; height: {size}px; position: relative">
  <svg class="voice-orb-svg" (absolute, full size)>
    <circle class="orb-ring-outer" />   ← THINKING/ACTING arc
    <circle class="orb-ring-inner" />   ← LISTENING breathing ring
  </svg>
  <div class="voice-orb voice-orb--{state.toLowerCase()}"
       style="width: {size*0.75}px; height: {size*0.75}px">
    <span class="voice-orb-icon">{STATE_ICONS[state]}</span>
  </div>
</div>
```

SVG ring details:
- Both circles are centered at `(size/2, size/2)`.
- Outer ring radius = `size * 0.45`. Stroke width = 1.5px. Color = `currentColor` (inherits from state class).
- Inner ring radius = `size * 0.35`. Stroke width = 2px.
- `stroke-dasharray` is set to the circumference (`2π·r`). `stroke-dashoffset` is animated for ACTING (progress arc) and UNDERSTANDING (scan sweep).
- For THINKING: the outer `<circle>` is wrapped in a `<g>` with `transform-origin: center` and `animation: orb-orbit 4s linear infinite`.
- For LISTENING: the inner `<circle>` gets `animation: orb-breathe-ring 3s ease-in-out infinite` (scale via SVG transform, not CSS).
- For SPEAKING: `audioLevel` prop drives `stroke-dashoffset` live to create a waveform-synced ring pulse.

State icon map (`STATE_ICONS`):

```js
const STATE_ICONS = {
  IDLE: '○', CONNECTING: '◌', LISTENING: '●', UNDERSTANDING: '◉',
  THINKING: '◌', ACTING: '⚡', SPEAKING: '◉', ESCALATING: '⚠',
  HUMAN_CONNECTED: '✓', ERROR: '✕',
}
```

The existing CSS classes `voice-orb--{state}` in `index.css` drive the orb's background, border, and box-shadow animations as before. The SVG layer adds the premium kinetic ring effects on top.

**How VoiceInterface uses VoiceOrb**:  
`VoiceInterface.jsx` replaces its inline orb `<div>` with `<VoiceOrb state={voiceState} onClick={isConnected ? disconnect : connect} audioLevel={...} />`. All Agora logic, polling, and state management remain inside `VoiceInterface`.

---

### `TranscriptConsole.jsx` (NEW)

**Responsibilities**: flat console-style transcript rendering, auto-scroll, animation.

```jsx
// Props
{
  messages: Array<{ role: string, content: string, time?: string, partial?: boolean }>,
  showToolAction?: boolean,
  toolSteps?: Array,  // passed to AIActionPanel
}
```

Layout: no chat bubbles. Each message is a `.tx-row` with CSS Grid `grid-template-columns: 80px 1fr`:

```jsx
<div className="tx-row" style={{ animationName: isNew ? 'tx-enter' : 'none' }}>
  <div className="tx-meta">
    <span className="t-label">{role === 'user' ? 'USER' : 'PRISM'}</span>
    {time && <span className="tx-time">{time}</span>}
  </div>
  <div className="tx-body">{content}{partial && <span className="tx-cursor" />}</div>
</div>
```

System event rows (role `'system'`) render as a full-width centered row:

```jsx
<div className="tx-row tx-row--system">
  <span>{content}</span>
</div>
```

Auto-scroll: a sentinel `<div ref={bottomRef} />` at the end. A scroll event listener on the scroll container sets `userScrolled = true` when `scrollTop + clientHeight < scrollHeight - 20`. When `userScrolled` is false, each new message calls `bottomRef.current.scrollIntoView({ behavior: 'smooth' })`. User scroll restores auto-scroll when they scroll back to the bottom.

---

### `IntelligencePanel.jsx` (REPLACES `ThinkingPanel.jsx`)

**Responsibilities**: vertical execution timeline, AI state display. Drop-in replacement.

```jsx
// Props — identical to ThinkingPanel
{
  voiceState: string,   // PRISM_STATE value
  aiState: object|null, // same shape as before
  compact?: boolean,
}
```

The existing `ThinkingPanel.jsx` file is renamed to `IntelligencePanel.jsx`. The import in `VoiceInterface.jsx` and `Agent.jsx` is updated. The props interface is preserved exactly — any consumer of `ThinkingPanel` works without modification.

**Full view** — vertical timeline with 5 named steps:

```js
const TIMELINE_STEPS = [
  { label: 'User intent detected',     states: ['LISTENING', 'UNDERSTANDING'] },
  { label: 'Context extracted',         states: ['UNDERSTANDING', 'THINKING'] },
  { label: 'Action identified',         states: ['THINKING', 'ACTING'] },
  { label: 'Verification',              states: ['ACTING'] },
  { label: 'Resolution / Escalation',  states: ['SPEAKING', 'ESCALATING', 'HUMAN_CONNECTED'] },
]
```

Step state: "done" (all states before current), "active" (current step), "pending" (future steps). Connector lines transition from `var(--border)` to `var(--ok)` as steps complete using CSS `transition: background 0.3s ease`.

**Compact view**: unchanged from existing `ThinkingPanel` compact — single row with state icon + label + confidence. The only visual change is the section header label changes from "AI State" to "PRISM INTELLIGENCE".

---

### `MetricCard.jsx` (NEW)

Simple presentational component used by the Overview page and Analytics stub.

```jsx
// Props
{
  label: string,
  value: string | number,
  sub?: string,
  color?: string,   // CSS custom property, default 'var(--text-primary)'
  trend?: 'up' | 'down' | null,
}
```

Renders with `.metric-card` class from existing CSS. No additional logic.

---

### `EscalationPanel.jsx` (MODIFIED)

Same props interface preserved:

```jsx
{ caseData, onTakeOver, compact = false }
```

Visual changes only: header transitions from `var(--danger-bg)` to `var(--surface-1)` (not `var(--ok-bg)`) on takeover, 400ms `transition: background 0.4s ease`. The compact variant is cleaned up to use the `.tx-row` layout language for consistency. No logic changes.

---

### `CasePanel.jsx` (MODIFIED)

Same props interface preserved:

```jsx
{ caseData }
```

Visual-only changes: replaces inline `style` objects with `className` references where CSS classes exist. The `Row` internal component is extracted to use `.tx-row` layout. No logic changes.

---

### `AIActionPanel.jsx` (MODIFIED)

Same props interface preserved:

```jsx
{ steps, compact }
```

Visual-only changes: header label changes to "Tool Execution" (already is). Progress dots in compact view use the `.status-dot` classes instead of inline style objects.

---

### New page components

#### `EscalationsPage.jsx` (NEW)

Receives `displayCases` and `onTakeOver` from `Agent.jsx`.

```jsx
// Props
{ cases: Array, onTakeOver: (caseId) => void, demoMode: boolean }
```

Renders each case where `case.escalated === true` as a full `EscalationPanel` (non-compact). If no escalated cases, renders empty state: centered "No active escalations" in `color: var(--text-muted)`.

#### `AnalyticsPage.jsx` (NEW)

Receives `displayCases` from `Agent.jsx`. Renders stub metric cards with values derived from DEMO_CASES (resolution rate, escalation rate, average confidence). Clearly labels all content with a `t-label` badge "DEMO DATA".

#### `AgentsPage.jsx` (NEW)

Receives `displayCases` from `Agent.jsx`. Renders two placeholder agent rows (Agent A, Agent B) with online/offline status dots and active case counts derived from case data. Stub only — no backend connectivity.

---

## Data Models

No new data models are introduced. All data shapes are unchanged from the existing codebase.

### `aiState` shape (unchanged)

```ts
{
  intent?: string,
  language?: string[],
  confidence?: number,          // 0-100
  confidence_label?: string,
  confidence_fields?: Record<string, 'HIGH'|'LOW'|'CRITICAL_UNKNOWN'>,
  verified?: string[],
  unverified?: string[],
  action?: string,
  tool?: string,
  tool_status?: 'running'|'completed'|'failed',
  tool_result?: { amount?, status?, order_status? },
  phase?: string,               // maps to voiceState
  summary?: string,
}
```

### `caseData` shape (unchanged)

Same as `DEMO_CASES` entries in `Agent.jsx`. No new fields added.

### Internal CSS variable additions

| Variable | Value | Purpose |
|---|---|---|
| `--sidebar-width` | `232px` (dynamic) | Shell grid column |
| `--topbar-height` | `52px` | Shell grid row |
| `--neu-out` | already exists | VoiceOrb idle shadow |

---

## Correctness Properties

### Property 1: VoiceOrb CSS class completeness

*For any* value in `PRISM_STATES`, the CSS class `voice-orb--{state.toLowerCase()}` must be defined in `index.css` and must produce a visually distinct appearance (non-empty rule block).

**Validates: Requirements 3.2, 3.3–3.12, 15.12**

### Property 2: Transcript role label invariant

*For any* array of messages passed to `TranscriptConsole`, every message with `role === 'user'` must render the label "USER" and every message with `role === 'assistant'` must render the label "PRISM" — the only visual distinction between the two roles is this label; no color, background, or positional distinction is applied to the message body.

**Validates: Requirements 4.7**

### Property 3: Confidence threshold coloring

*For any* numeric confidence value `c` in the range [0, 100], the color applied to the confidence display must satisfy:
- `c >= 70` → `var(--ok)`
- `40 <= c < 70` → `var(--warn)`
- `c < 40` → `var(--danger)`

This property must hold in `IntelligencePanel`, `EscalationPanel`, and `CasePanel` independently.

**Validates: Requirements 5.8, 12.6**

### Property 4: Badge renders for all positive counts

*For any* badge count `n > 0` assigned to a sidebar navigation item, a `.nav-item__badge` element must be present in the DOM for that item. *For any* badge count `n === 0`, no badge element must be rendered.

**Validates: Requirements 1.8**

### Property 5: Shell renders on every route

*For any* valid application route (`/` or `/agent`), the rendered output must contain both a Sidebar element (with PRISM logotype) and a TopBar element (with page title).

**Validates: Requirements 1.1, 6.1**

### Property 6: Functional API contract preservation

*For any* user session flow (connect → interact → disconnect), the set of outbound API calls — their URLs, HTTP methods, and request body shapes — must be identical to the pre-redesign baseline. Specifically:
- `POST /session/start` with `{ channel, user_uid, language, locale }`
- `POST /session/stop` with `{ agent_id, channel }`
- `GET /state/{channel}` (polled at 1500ms)
- `GET /active-state` (polled at 2000ms)
- `POST /cases/{id}/takeover`
- `POST /chat` with `{ message, channel, language }`
- `POST /asr` with `FormData { audio, language }`
- `GET /token?channel=...&uid=...`

**Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.9**

---

## Error Handling

### Backend unreachable

All existing fallback logic is preserved unchanged:
- `VoiceInterface` enters `demoMode = true` when token fetch or session start fails.
- `Agent.jsx` enters `demoMode = true` when `/cases` returns non-OK or non-JSON.
- TopBar shows backend status indicator using `backendError` state — no blocking UI.

### Agora connection failures

Existing `try/catch` in `connect()` and `handleAgentAgoraJoin()` preserved verbatim. On failure, `setStatus('error')` and `setError(message)` as before. VoiceOrb renders `voice-orb--error` class.

### Sidebar collapse at small viewports

At `< 768px`: sidebar does not collapse — it is replaced by a bottom navigation bar (CSS media query). The `sidebarExpanded` state is irrelevant at this breakpoint; the bottom nav is always visible.

### Escalation takeover failure

`EscalationPanel` existing `try/catch` around the POST is preserved. If the request fails, `setTaking(false)` and the button is re-enabled. No new error UI added — existing behavior maintained.

---

## Testing Strategy

### Unit tests

Unit tests verify specific examples, edge cases, and integration points. Written with Vitest (already the Vite ecosystem standard, zero config needed).

Key examples to test:
- `AppShell` renders `<Sidebar>` and `<TopBar>` for both `/` and `/agent` routes (verifies Property 5)
- `Sidebar` renders badge when `escalations > 0`, no badge when `escalations === 0` (verifies Property 4)
- `IntelligencePanel` renders correct step states for each `voiceState` value
- `EscalationPanel` header background is `var(--danger-bg)` before takeover, `var(--surface-1)` after
- `TranscriptConsole` renders USER label for `role: 'user'`, PRISM label for `role: 'assistant'` (verifies Property 2 via example)
- `VoiceOrb` applies `voice-orb--listening` class when `state === 'LISTENING'`
- `connect()` in `VoiceInterface` calls `POST /session/start` with correct body shape (verifies Property 6)

Edge cases:
- Empty `messages` array: `TranscriptConsole` renders empty state without error
- `aiState === null`: `IntelligencePanel` renders pipeline without crashing
- `confidence === 0` and `confidence === 100`: both render without error and use correct colors
- `sidebarExpanded` toggle: CSS variable `--sidebar-width` is set correctly

### Property-based tests

Use [fast-check](https://github.com/dubzzz/fast-check) — the standard PBT library for JavaScript/TypeScript. Minimum 100 iterations per property test.

**Test configuration tag format: `Feature: prism-dashboard-redesign, Property {N}: {property_text}`**

#### Property 1: VoiceOrb CSS class completeness
```
Feature: prism-dashboard-redesign, Property 1: VoiceOrb CSS class completeness
```
Generator: `fc.constantFrom(...PRISM_STATES)` — samples from the 10 known states.  
Assertion: for each sampled state, `document.querySelector('.voice-orb--' + state.toLowerCase())` must exist (or the CSS rule must be parseable from the stylesheet text). Alternatively: render `<VoiceOrb state={state} onClick={()=>{}} />` and assert the element has the expected className.

#### Property 2: Transcript role label invariant
```
Feature: prism-dashboard-redesign, Property 2: Transcript role label invariant
```
Generator: `fc.array(fc.record({ role: fc.constantFrom('user', 'assistant'), content: fc.string({ minLength: 1 }) }), { minLength: 1, maxLength: 50 })` — generates varied message arrays.  
Assertion: render `<TranscriptConsole messages={messages} />`. For every message where `role === 'user'`, assert the rendered label text equals "USER". For every `role === 'assistant'`, assert label equals "PRISM". Assert no `background-color` difference between user and agent message body elements.

#### Property 3: Confidence threshold coloring
```
Feature: prism-dashboard-redesign, Property 3: Confidence threshold coloring
```
Generator: `fc.integer({ min: 0, max: 100 })` — generates confidence values across the full range.  
Assertion: for a given `confidence` value, render the confidence display section of `IntelligencePanel` with `aiState={{ confidence }}` and assert the color applied matches the threshold rule: `>= 70` → ok, `40-69` → warn, `< 40` → danger. Run for all three components independently.

#### Property 4: Badge renders for all positive counts
```
Feature: prism-dashboard-redesign, Property 4: Badge renders for all positive counts
```
Generator: `fc.nat({ max: 99 })` for counts including 0.  
Assertion: render `<Sidebar badges={{ escalations: count }} ... />`. When `count > 0`, assert `.nav-item__badge` is present in the escalations item. When `count === 0`, assert no badge element is rendered.

#### Property 5: Shell renders on every route
```
Feature: prism-dashboard-redesign, Property 5: Shell renders on every route
```
Generator: `fc.constantFrom('/', '/agent')`.  
Assertion: render the full app at each route path (using `MemoryRouter`). Assert the rendered output contains a sidebar element with PRISM logotype text and a topbar element with a non-empty page title.

#### Property 6: Functional API contract preservation
```
Feature: prism-dashboard-redesign, Property 6: Functional API contract preservation
```
Generator: `fc.record({ channel: fc.constantFrom('prism-demo', 'prism-text'), language: fc.constantFrom('en', 'hi'), uid: fc.integer({ min: 10000, max: 99999 }) })`.  
Assertion: mock `fetch` with a spy. Trigger a `connect()` call in `VoiceInterface` with the generated params. Assert that `POST /session/start` was called with a body containing `channel`, `user_uid`, `language`, and `locale` — no extra fields, none missing. Repeat for `disconnect()` asserting `POST /session/stop` shape.

### Testing notes

- Property tests run via `vitest --run` (single execution, no watch mode).
- JSDOM environment for component rendering.
- Agora SDK mocked globally in test setup — it requires browser APIs unavailable in JSDOM.
- `ttsManager` mocked to no-op in all tests — TTS requires real browser speech synthesis.
- `fetch` mocked with `vi.fn()` returning sensible JSON payloads for API contract tests.
- CSS variable assertions use `getComputedStyle` where possible; CSS rule text assertions parse the imported stylesheet.
