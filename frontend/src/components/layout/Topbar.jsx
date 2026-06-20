import { Link } from 'react-router-dom';

export default function Topbar({ title, breadcrumbs = [] }) {
  return (
    <header className="h-14 flex items-center px-6 gap-2 text-sm"
      style={{ background: '#FAF9F5', borderBottom: '1px solid #E8E2D0', color: '#B8AF9C' }}>
      {breadcrumbs.map((b, i) => (
        <span key={i} className="flex items-center gap-2">
          {b.to ? (
            <Link to={b.to} style={{ color: '#B8AF9C', textDecoration: 'none' }}
              onMouseEnter={(e) => { e.target.style.color = '#14211A'; }}
              onMouseLeave={(e) => { e.target.style.color = '#B8AF9C'; }}>
              {b.label}
            </Link>
          ) : (
            <span style={{ color: '#14211A', fontWeight: 600 }}>{b.label}</span>
          )}
          {i < breadcrumbs.length - 1 && <span style={{ color: '#E8E2D0' }}>/</span>}
        </span>
      ))}
      {breadcrumbs.length === 0 && (
        <span style={{ color: '#14211A', fontWeight: 600 }}>{title}</span>
      )}
    </header>
  );
}
