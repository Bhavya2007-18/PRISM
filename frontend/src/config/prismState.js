/**
 * PRISM State — the single shared operational-state contract (frontend mirror).
 *
 * This file MUST stay in sync with backend/prism_state.py: identical names,
 * identical order. The backend derives these values (derive_voice_state) and
 * ships them over /state and /active-state; the ThinkingPanel renders them via
 * PRISM_STATE_CONFIG. Together they are the one shared PrismState definition
 * referenced by PRD §12 / tech-stack §27.
 */

// Canonical ordered list — mirror of PRISM_STATES in backend/prism_state.py.
export const PRISM_STATES = [
  'IDLE',            // no active session
  'CONNECTING',      // joining the Agora channel
  'LISTENING',       // session live, awaiting speech
  'UNDERSTANDING',   // user spoke, parsing intent
  'THINKING',        // reasoning / choosing next action
  'ACTING',          // running a tool (e.g. check_transaction)
  'SPEAKING',        // delivering a resolution
  'ESCALATING',      // handing off to a human
  'HUMAN_CONNECTED', // human agent has taken over
  'ERROR',           // unrecoverable error
]

// Presentation metadata for each state (icon / color / label).
export const PRISM_STATE_CONFIG = {
  IDLE:            { icon: '○',  color: '#565674', label: 'Idle' },
  CONNECTING:      { icon: '◌',  color: '#60a5fa', label: 'Connecting' },
  LISTENING:       { icon: '🎙', color: '#34d399', label: 'Listening' },
  UNDERSTANDING:   { icon: '◉',  color: '#a78bfa', label: 'Understanding' },
  THINKING:        { icon: '◌',  color: '#7c6fff', label: 'Thinking' },
  ACTING:          { icon: '⚡',  color: '#fbbf24', label: 'Checking' },
  SPEAKING:        { icon: '🔊', color: '#34d399', label: 'Speaking' },
  ESCALATING:      { icon: '⚠',  color: '#f87171', label: 'Escalating' },
  HUMAN_CONNECTED: { icon: '🟢', color: '#34d399', label: 'Human Connected' },
  ERROR:           { icon: '✕',  color: '#f87171', label: 'Error' },
}
