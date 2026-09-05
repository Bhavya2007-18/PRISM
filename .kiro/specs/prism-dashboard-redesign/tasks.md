# Implementation Plan: PRISM Dashboard Redesign

## Overview

Transform the PRISM frontend from two disconnected pages into a production-grade AI Operations SaaS platform. The implementation proceeds foundation-first: CSS tokens → shared shell components → core voice components → updated existing components → new page components → page refactors → wiring → tests → mobile → final polish. All backend contracts, Agora integrations, and API shapes are preserved verbatim throughout.

## Tasks

- [x] 1. Update `index.css` — design tokens and keyframes
  - Verify all existing design tokens are present (`--surface-0..4`, `--dark-0..4`, `--text-*`, `--border-*`, `--ok/warn/danger` with bg/border variants, `--font-sans/mono`, `--r-*`, `--shadow-*`, `--t-*`, `--neu-out`, `--sidebar-width: 232px`, `--topbar-height: 52px`)
  - Add any missing tokens from the design token spec (Req 2)
  - Add `orb-orbit` and `orb-breathe-ring` keyframes for SVG ring animations (used by VoiceOrb)
  - Add VoiceOrb SVG wrapper classes: `.voice-orb-wrapper`, `.voice-orb-svg`, `.voice-orb-icon`
  - Add `.tx-row`, `.tx-row--system`, `.tx-meta`, `.tx-body`, `.tx-time`, `.tx-cursor` classes for TranscriptConsole
  - Add `.nav-item__badge` if not already present
  - Add `app-shell` grid layout with CSS variable `--sidebar-width` driving the column width (override to `72px` when collapsed)
  - Verify `voice-orb--{state}` classes exist for all 10 PRISM_STATES (idle, connecting, listening, understanding, thinking, acting, speaking, escalating, human_connected, error)
  - Add `@media (max-width: 768px)` stubs for bottom nav and bottom sheet (populated fully in task 9)
  - _Requirements: 2.1–2.11, 3.2–3.13, 4.1–4.8, 13.5, 13.7, 13.8, 16.1–16.5_

  - [x] 1.1 Audit and patch design tokens in `frontend/src/index.css`
    - Read the current `index.css` and diff against the full token list in Req 2
    - Add any missing tokens; do not remove or rename any existing tokens or class names
    - _Requirements: 2.1–2.11, 16.1–16.5_

  - [x] 1.2 Add new CSS classes and keyframes to `frontend/src/index.css`
    - Append `.voice-orb-wrapper`, `.voice-orb-svg`, `.voice-orb-icon` rules
    - Append `.tx-row`, `.tx-row--system`, `.tx-meta`, `.tx-body`, `.tx-time`, `.tx-cursor` rules
    - Append `orb-orbit` and `orb-breathe-ring` keyframes
    - Append `voice-orb--understanding` keyframe if missing
    - _Requirements: 3.2–3.13, 4.1–4.8, 13.5_

- [x] 2. Build `AppShell.jsx`, `Sidebar.jsx`, and `TopBar.jsx`

  - [x] 2.1 Create `frontend/src/components/AppShell.jsx`
    - Implement CSS Grid shell: `grid-template-columns: var(--sidebar-width) 1fr`, `grid-template-rows: var(--topbar-height) 1fr`, `height: 100vh`, `overflow: hidden`
    - Hold `sidebarExpanded: boolean` state; toggle handler overrides `--sidebar-width` inline to `72px` or `232px`
    - Accept `sidebarBadges?: { escalations?: number }`, `pageTitle?: string`, `connectionStatus?` props
    - Render `<Sidebar>`, `<TopBar>`, and `<Outlet />` (React Router v6) in the three grid areas
    - Pass `expanded`, `onToggle`, `badges`, `activeRoute` (from `useLocation`), and `activeIntraNav` down to Sidebar
    - _Requirements: 1.1, 1.14, 6.1_

  - [x] 2.2 Create `frontend/src/components/Sidebar.jsx`
    - Render dark sidebar: `background: var(--dark-1)`, `border-right: 1px solid var(--dark-border)`
    - Show PRISM logotype: `font-weight: 700`, `font-size: 20px`, `color: var(--dark-text-primary)`; collapse to "P" when `expanded === false`
    - Implement PRIMARY_NAV (Overview, Live Sessions, Cases, Escalations, Agents, Analytics, Live Session link) and SECONDARY_NAV (Integrations, Settings) from design spec
    - Active item: `background: var(--dark-3)`, `color: var(--dark-text-primary)`; hover: `background: var(--dark-2)`, `transition: 100ms ease`
    - When `expanded === false`: hide labels via `opacity: 0; width: 0; overflow: hidden` with CSS transition; show icons only
    - Render `.nav-item__badge` on Escalations item when `badges.escalations > 0`; hide badge when `badges.escalations === 0`
    - Animate width transition over 200ms ease (Req 1.10)
    - Bottom section: user profile / status indicator (static placeholder)
    - _Requirements: 1.2–1.10_

  - [x] 2.3 Create `frontend/src/components/TopBar.jsx`
    - Props: `title`, `demoMode?`, `connectionStatus?`, `lastUpdated?`, `onToggleSidebar`
    - Layout: `display: flex; align-items: center; padding: 0 24px; gap: 16px`; `background: var(--surface-0)`; `border-bottom: 1px solid var(--border)` (Req 1.13)
    - Left: page title in `font-size: 15px`, `font-weight: 600` (Req 1.11); "DEMO" badge when `demoMode` is true
    - Right: connection status dot (`.status-dot--ok` / `.status-dot--danger`), notification icon (static bell), user avatar chip
    - _Requirements: 1.11–1.13, 1.15_

- [x] 3. Build `VoiceOrb.jsx`
  - [x] 3.1 Create `frontend/src/components/VoiceOrb.jsx`
    - Props: `state: string`, `onClick: () => void`, `size?: number` (default 160), `audioLevel?: number`
    - Render outer wrapper div `.voice-orb-wrapper` at `{size}px × {size}px`, `position: relative`
    - Render SVG `.voice-orb-svg` (absolute, full size) with two `<circle>` elements: outer ring (radius `size * 0.45`, stroke 1.5px) and inner ring (radius `size * 0.35`, stroke 2px); set `stroke-dasharray` to circumference for each
    - Render inner div `className={\`voice-orb voice-orb--\${state.toLowerCase()}\`}` at `size * 0.75` diameter, containing `.voice-orb-icon` with `STATE_ICONS[state]`
    - THINKING: add `orb-orbit 4s linear infinite` animation on SVG outer ring `<g>`
    - LISTENING: add `orb-breathe-ring 3s ease-in-out infinite` on inner SVG circle
    - ACTING: animate `stroke-dashoffset` on outer ring for progress arc
    - SPEAKING: drive `stroke-dashoffset` from `audioLevel` prop for waveform-synced pulse
    - Do NOT add any business logic, API calls, or state management — presentational only
    - Do NOT change how `VoiceInterface.jsx` manages state; it will replace its inline orb div with `<VoiceOrb>` in task 6.1
    - _Requirements: 3.1–3.16, 15.12_

  - [ ]* 3.2 Write property test for VoiceOrb CSS class completeness (Property 1)
    - **Property 1: VoiceOrb CSS class completeness**
    - **Validates: Requirements 3.2, 3.3–3.12, 15.12**
    - Use `fc.constantFrom(...PRISM_STATES)` generator
    - Render `<VoiceOrb state={state} onClick={()=>{}} />` for each sampled state
    - Assert the rendered element has className containing `voice-orb--{state.toLowerCase()}`
    - Tag: `Feature: prism-dashboard-redesign, Property 1: VoiceOrb CSS class completeness`

- [x] 4. Build `TranscriptConsole.jsx`
  - [x] 4.1 Create `frontend/src/components/TranscriptConsole.jsx`
    - Props: `messages: Array<{ role, content, time?, partial? }>`, `showToolAction?`, `toolSteps?`
    - Render each message as `.tx-row` with CSS Grid `grid-template-columns: 80px 1fr`
    - USER messages: label "USER"; assistant messages: label "PRISM" — label only, no color or background distinction on the message body (Req 4.7)
    - System event messages: full-width `.tx-row.tx-row--system` centered row
    - Animate new rows with `tx-enter` keyframe (220ms)
    - Partial/live transcript: show `.tx-cursor` blinking cursor (Req 4.5)
    - Auto-scroll: sentinel `<div ref={bottomRef} />` at end; detect user scroll via `scrollTop + clientHeight < scrollHeight - 20` and set `userScrolled` flag; resume auto-scroll when user scrolls back to bottom (Req 4.6)
    - Timestamps in `font-family: var(--font-mono)`, `font-size: 10px`, `color: var(--text-muted)` (Req 4.4)
    - _Requirements: 4.1–4.8_

  - [ ]* 4.2 Write property test for transcript role label invariant (Property 2)
    - **Property 2: Transcript role label invariant**
    - **Validates: Requirements 4.7**
    - Generator: `fc.array(fc.record({ role: fc.constantFrom('user','assistant'), content: fc.string({ minLength:1 }) }), { minLength:1, maxLength:50 })`
    - Render `<TranscriptConsole messages={messages} />` and assert USER label for `role:'user'`, PRISM label for `role:'assistant'`
    - Assert no `background-color` difference between user and agent message body elements
    - Tag: `Feature: prism-dashboard-redesign, Property 2: Transcript role label invariant`

- [x] 5. Build `IntelligencePanel.jsx` (replaces `ThinkingPanel.jsx`)
  - [x] 5.1 Create `frontend/src/components/IntelligencePanel.jsx`
    - Props: identical to `ThinkingPanel` — `voiceState: string`, `aiState: object|null`, `compact?: boolean`
    - Full view: vertical timeline with 5 named steps (User intent detected → Context extracted → Action identified → Verification → Resolution/Escalation)
    - Step states: "done" (idx < activeIdx), "active" (current), "pending" (future)
    - Done dot: filled `var(--ok)`, 300ms transition; active dot: `var(--text-primary)` with `box-shadow: 0 0 0 3px rgba(0,0,0,0.07)` pulse; pending dot: `var(--surface-3)` with `border: 1.5px solid var(--border-strong)` (Req 5.3–5.5)
    - Connector lines: transition from `var(--border)` to `var(--ok)` as steps complete, 300ms ease (Req 5.6)
    - Display intent, language, confidence, verified, unverified, tool info from `aiState` prop when present (Req 5.7–5.10)
    - Compact view: single-line status bar identical to existing `ThinkingPanel` compact, with section header label changed to "PRISM INTELLIGENCE" (Req 5.11)
    - Confidence coloring: ≥70 → `var(--ok)`, 40–69 → `var(--warn)`, <40 → `var(--danger)` (Req 5.8)
    - Update `import ThinkingPanel` → `import IntelligencePanel` in `VoiceInterface.jsx` and `Agent.jsx`
    - _Requirements: 5.1–5.13, 15.11_

  - [ ]* 5.2 Write property test for confidence threshold coloring (Property 3)
    - **Property 3: Confidence threshold coloring**
    - **Validates: Requirements 5.8, 12.6**
    - Generator: `fc.integer({ min:0, max:100 })`
    - Render `IntelligencePanel` with `aiState={{ confidence }}` and assert correct color token per threshold
    - Run equivalent assertions for `EscalationPanel` and `CasePanel` components independently
    - Tag: `Feature: prism-dashboard-redesign, Property 3: Confidence threshold coloring`

- [x] 6. Checkpoint — core components complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Update existing components — visual-only changes, same props

  - [x] 7.1 Update `frontend/src/components/EscalationPanel.jsx`
    - Visual changes only; preserve `{ caseData, onTakeOver, compact }` props interface exactly (Req 15.11)
    - Header: transition from `var(--danger-bg)` to `var(--surface-1)` (not `var(--ok-bg)`) on takeover, 400ms `transition: background 0.4s ease` (Req 9.4, 12.4)
    - Compact variant: clean up to use `.tx-row` layout language for consistency
    - No logic changes; preserve existing `try/catch` around POST and `setTaking(false)` re-enable on failure
    - _Requirements: 9.1–9.7, 12.1–12.11_

  - [x] 7.2 Update `frontend/src/components/CasePanel.jsx`
    - Visual changes only; preserve `{ caseData }` prop interface exactly (Req 15.11)
    - Replace inline `style` objects with `className` references where CSS classes already exist
    - Extract internal `Row` to use `.tx-row` layout language
    - No logic changes
    - _Requirements: 8.7_

  - [x] 7.3 Update `frontend/src/components/AIActionPanel.jsx`
    - Visual changes only; preserve `{ steps, compact }` prop interface exactly (Req 15.11)
    - Compact view: replace inline style progress dots with `.status-dot` CSS classes
    - Header label already reads "Tool Execution" — no change needed
    - No logic changes
    - _Requirements: 8.6_

- [x] 8. Create new page sub-components

  - [x] 8.1 Create `frontend/src/components/EscalationsPage.jsx`
    - Props: `{ cases: Array, onTakeOver: (caseId) => void, demoMode: boolean }`
    - Render each case where `case.escalated === true` as a full (non-compact) `EscalationPanel`
    - Empty state: centered "No active escalations" in `color: var(--text-muted)` when no escalated cases (Req 9.6)
    - In `demoMode`, filter `DEMO_CASES` to `escalated === true` (Req 9.7)
    - _Requirements: 9.1–9.7_

  - [x] 8.2 Create `frontend/src/components/AnalyticsPage.jsx`
    - Props: `{ cases: Array, demoMode: boolean }`
    - Derive metrics from `cases`: resolution rate, escalation rate, avg confidence
    - Render stub metric cards using `.metric-card` class; label all content with `t-label` "DEMO DATA" in `color: var(--text-muted)` (Req 11.1–11.3, 11.6)
    - _Requirements: 11.1–11.3, 11.6_

  - [x] 8.3 Create `frontend/src/components/AgentsPage.jsx`
    - Props: `{ cases: Array, demoMode: boolean }`
    - Render two placeholder agent rows (Agent A, Agent B) with online/offline `.status-dot` and active case count derived from `cases` (Req 11.4–11.5)
    - Label with `t-label` "DEMO DATA" (Req 11.6)
    - _Requirements: 11.4–11.6_

- [x] 9. Update `Caller.jsx` — Live Session page inside AppShell

  - [x] 9.1 Refactor `frontend/src/pages/Caller.jsx` to three-column layout
    - Remove the outer full-page centering wrapper; `Caller` now renders only workspace content (AppShell provides the shell)
    - Implement three-column desktop layout: left context column, center (VoiceOrb + TranscriptConsole), right (IntelligencePanel + Case Context)
    - Replace the existing inline orb `<div>` in `VoiceInterface.jsx` with `<VoiceOrb state={voiceState} onClick={isConnected ? disconnect : connect} audioLevel={...} />`; keep all Agora logic, polling, and state management inside `VoiceInterface`
    - Replace `ThinkingPanel` usage with `IntelligencePanel` in `VoiceInterface.jsx`
    - Replace transcript rendering with `TranscriptConsole` component
    - Preserve language selector, mode toggle (Voice/Text), TTS greeting, demo mode, all Agora join/publish/subscribe logic, connect/disconnect flow, quick phrase pills, sendChatMessage, ASR mic recording, and ttsManager usage verbatim (Req 15.1–15.9)
    - Display Escalation_Card inline below transcript when escalated (not as a toast) (Req 6.9)
    - Add "Agent Dashboard →" link at bottom right (Req 6.10)
    - Do NOT change: `getApiUrl`, `PRISM_STATE_CONFIG`, `PRISM_STATES`, `LANGUAGES`, `getLanguageConfig`, `ttsManager`, channel names `prism-demo`/`prism-text`, agent UID 12345
    - _Requirements: 6.1–6.12, 15.1–15.12_

- [x] 10. Update `Agent.jsx` — expanded navigation and new sub-pages

  - [x] 10.1 Refactor `frontend/src/pages/Agent.jsx` to use expanded navigation
    - Remove inline `Sidebar` and `TopBar` component definitions (now provided by AppShell)
    - Expand `activeNav` state to include all new nav items: `overview`, `cases`, `history`, `escalations`, `agents`, `analytics`
    - Pass `escalationCount` (count of `activeCases`) up to AppShell via `sidebarBadges` prop
    - Wire `activeNav` changes through sidebar navigation (AppShell receives `activeIntraNav` from Agent and passes to Sidebar)
    - Add `EscalationsPage`, `AnalyticsPage`, `AgentsPage` imports and render them in `{activeNav === 'escalations' && <EscalationsPage .../>}` etc.
    - Add filter pills to `HistoryPage` inline component: All, Open, AI Resolved, Escalated, Human Active (Req 10.2–10.3)
    - Preserve all polling loops (cases at 3000ms, active-state at 2000ms), DEMO_CASES, DEMO_CONV, Agora agent join/leave logic, takeover flow, and demoMode fallback verbatim (Req 15.1–15.9)
    - Do NOT change: `getApiUrl`, channel names, agent UID 88888
    - _Requirements: 7.1–7.9, 8.1–8.13, 10.1–10.6, 15.1–15.12_

- [x] 11. Wire `App.jsx` — wrap routes in AppShell via React Router v6 Outlet

  - [x] 11.1 Update `frontend/src/App.jsx`
    - Import `AppShell` and restructure routes so both `/` and `/agent` are children of a `<Route element={<AppShell />}>` parent
    - `AppShell` renders `<Outlet />` in the workspace area
    - Pass `sidebarBadges`, `pageTitle`, and `connectionStatus` as props into `AppShell` from route-level context or via a thin wrapper
    - Verify React Router v6 `useLocation` in Sidebar correctly activates route-level nav items
    - _Requirements: 1.1, 6.1_

  - [ ]* 11.2 Write property test for shell renders on every route (Property 5)
    - **Property 5: Shell renders on every route**
    - **Validates: Requirements 1.1, 6.1**
    - Generator: `fc.constantFrom('/', '/agent')`
    - Render full app at each route using `MemoryRouter`; assert output contains sidebar element with PRISM logotype and topbar element with non-empty page title
    - Tag: `Feature: prism-dashboard-redesign, Property 5: Shell renders on every route`

- [-] 12. Set up Vitest and write remaining property-based tests

  - [~] 12.1 Install and configure Vitest + fast-check + jsdom + React Testing Library
    - Add `vitest`, `@vitest/ui`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `fast-check` to `devDependencies` in `frontend/package.json` with pinned versions
    - Add `vitest.config.js` (or update `vite.config.js`) with `environment: 'jsdom'`, global Agora SDK mock, and `ttsManager` no-op mock in a `setupFiles` file
    - Add `"test": "vitest --run"` script to `frontend/package.json`
    - _Requirements: Design §Testing Strategy_

  - [ ]* 12.2 Write property test for badge renders for all positive counts (Property 4)
    - **Property 4: Badge renders for all positive counts**
    - **Validates: Requirements 1.8**
    - Generator: `fc.nat({ max: 99 })`
    - Render `<Sidebar badges={{ escalations: count }} expanded={true} onToggle={()=>{}} activeRoute="/agent" />`
    - When `count > 0`: assert `.nav-item__badge` is present in escalations item; when `count === 0`: assert no badge element
    - Tag: `Feature: prism-dashboard-redesign, Property 4: Badge renders for all positive counts`

  - [ ]* 12.3 Write property test for functional API contract preservation (Property 6)
    - **Property 6: Functional API contract preservation**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.9**
    - Generator: `fc.record({ channel: fc.constantFrom('prism-demo','prism-text'), language: fc.constantFrom('en','hi'), uid: fc.integer({ min:10000, max:99999 }) })`
    - Mock `fetch` with `vi.fn()`. Trigger `connect()` in `VoiceInterface`; assert `POST /session/start` called with body containing `channel`, `user_uid`, `language`, `locale` — no extra fields, none missing
    - Trigger `disconnect()`; assert `POST /session/stop` called with body containing `agent_id` and `channel`
    - Tag: `Feature: prism-dashboard-redesign, Property 6: Functional API contract preservation`

- [x] 13. Checkpoint — all components wired and tests configured
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Mobile responsiveness

  - [x] 14.1 Add mobile CSS and bottom navigation in `frontend/src/index.css` and `Sidebar.jsx`
    - `@media (max-width: 768px)`: hide `.app-sidebar`, change `app-shell` grid to `grid-template-columns: 1fr`, add `.bottom-nav` bar at `position: fixed; bottom: 0; background: var(--dark-1)` with icon-only nav items (Req 14.1, 14.6)
    - Caller_Page: VoiceOrb full-width, centered on screen as primary element (Req 14.2)
    - metric cards on Overview: `grid-template-columns: 1fr` in media query (Req 14.4)
    - Cases 3-col: collapse to single scrollable column with a tab bar (List, Transcript, Intelligence) (Req 14.5)
    - _Requirements: 14.1–14.6_

  - [x] 14.2 Add bottom sheet component for Intelligence and Case Context on mobile
    - Create simple `BottomSheet.jsx` with slide-up animation, `backdrop: rgba(0,0,0,0.4)` with 200ms fade (Req 14.7)
    - Integrate into Caller_Page: slide up from bottom when user taps an "Info" trigger; contains IntelligencePanel + Case Context (Req 14.3)
    - _Requirements: 14.3, 14.7_

- [x] 15. Final verification — functional preservation constraints (Req 15)

  - [x] 15.1 Audit and verify all functional preservation constraints
    - Read `VoiceInterface.jsx` and confirm: `AgoraRTC.createClient`, `client.join`, `client.publish`, `client.subscribe`, `client.leave`, `user-published`/`user-unpublished` handlers are all intact (Req 15.1)
    - Confirm `/session/start` and `/session/stop` POST calls have identical bodies (Req 15.2)
    - Confirm voice state polling at 1500ms on `/state/{channel}` and agent state polling at 2000ms on `/active-state` are intact (Req 15.3)
    - Confirm `ttsManager.speak`, `ttsManager.cancel`, and `prismSpeaking` state callbacks are unchanged (Req 15.4)
    - Confirm `sendChatMessage`, `POST /chat`, `getDemoReply`, ASR mic recording via `POST /asr` are unchanged (Req 15.5)
    - Confirm `setEscalated`, `setEscalatedCaseId`, `setTakenOver` are triggered from polling responses correctly (Req 15.6)
    - Confirm `DEMO_CASES`, `DEMO_CONV`, and `demoMode` fallback are preserved (Req 15.7)
    - Confirm `getApiUrl`, `PRISM_STATE_CONFIG`, `PRISM_STATES`, `LANGUAGES`, `getLanguageConfig` are never modified (Req 15.8)
    - Confirm channel names `prism-demo`/`prism-text` and agent UIDs 12345/88888 are unchanged (Req 15.10)
    - Confirm `voice-orb voice-orb--{state.toLowerCase()}` class pattern is used in `VoiceOrb.jsx` (Req 15.12)
    - _Requirements: 15.1–15.12_

- [x] 16. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Tasks 12.1 (Vitest setup) must be completed before any `*` property test tasks run
- All tasks reference specific requirements for traceability
- Checkpoints at tasks 6, 13, and 16 ensure incremental validation
- Property tests validate universal correctness properties; unit tests validate specific examples and edge cases
- The `IntelligencePanel` rename is the only file-rename in this spec; all other changes are additive or in-place edits
- The design uses JavaScript (JSX) with Vitest + fast-check as the test stack — no TypeScript migration is implied
- **Critical**: tasks 9.1 and 10.1 are the most complex; read both files completely before editing

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3"] },
    { "id": 2, "tasks": ["3.1", "4.1", "5.1", "7.1", "7.2", "7.3"] },
    { "id": 3, "tasks": ["3.2", "4.2", "5.2", "8.1", "8.2", "8.3"] },
    { "id": 4, "tasks": ["9.1", "10.1"] },
    { "id": 5, "tasks": ["11.1"] },
    { "id": 6, "tasks": ["11.2", "12.1"] },
    { "id": 7, "tasks": ["12.2", "12.3"] },
    { "id": 8, "tasks": ["14.1"] },
    { "id": 9, "tasks": ["14.2"] },
    { "id": 10, "tasks": ["15.1"] }
  ]
}
```
