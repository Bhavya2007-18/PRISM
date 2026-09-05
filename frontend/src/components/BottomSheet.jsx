export default function BottomSheet({ isOpen, onClose, title, children }) {
  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="bottom-sheet-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Sheet */}
      <div
        className="bottom-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Info panel'}
      >
        <div className="bottom-sheet-handle" />
        {title && (
          <div style={{
            padding: '4px 20px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
              {title}
            </span>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: '4px 8px',
                borderRadius: 'var(--r-md)',
                fontSize: 14,
                color: 'var(--text-tertiary)',
              }}
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        )}
        <div style={{ padding: '0 4px 4px' }}>
          {children}
        </div>
      </div>
    </>
  )
}
