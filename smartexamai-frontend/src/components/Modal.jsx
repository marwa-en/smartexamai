export default function Modal({ title, onClose, children, width = 480 }) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ width: '100%', maxWidth: width, maxHeight: '90vh', overflowY: 'auto', margin: 16 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="card-header">
          <span className="card-title">{title}</span>
          <button className="btn-icon" onClick={onClose}>
            <span className="material-icons">close</span>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
