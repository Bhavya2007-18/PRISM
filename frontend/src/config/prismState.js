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
  'IDLE', 'CONNECTING', 'LISTENING', 'UNDERSTANDING', 'THINKING',
  'PLANNING', 'ACTING', 'VERIFYING', 'SPEAKING', 'ESCALATING',
  'HUMAN_CONNECTED', 'RESOLVED', 'FAILED', 'ENDED',
]

// Presentation metadata for each state (icon / color / label).
export const PRISM_STATE_CONFIG = {
  IDLE:            { icon: '○',  color: '#888888', label: 'Idle' },
  CONNECTING:      { icon: '◌',  color: '#888888', label: 'Connecting' },
  LISTENING:       { icon: '●',  color: '#444442', label: 'Listening' },
  UNDERSTANDING:   { icon: '◉',  color: '#444442', label: 'Understanding' },
  THINKING:        { icon: '◌',  color: '#333331', label: 'Thinking' },
  PLANNING:        { icon: '▣',  color: '#333331', label: 'Planning' },
  ACTING:          { icon: '→',  color: '#181818', label: 'Checking' },
  VERIFYING:       { icon: '◎',  color: '#181818', label: 'Verifying' },
  SPEAKING:        { icon: '◉',  color: '#181818', label: 'Speaking' },
  ESCALATING:      { icon: '⚠',  color: '#9B1A1A', label: 'Escalating' },
  HUMAN_CONNECTED: { icon: '✓',  color: '#1A6B3A', label: 'Human Active' },
  RESOLVED:        { icon: '✓',  color: '#1A6B3A', label: 'Resolved' },
  FAILED:          { icon: '✕',  color: '#9B1A1A', label: 'Error' },
  ENDED:           { icon: '○',  color: '#888888', label: 'Ended' },
}
