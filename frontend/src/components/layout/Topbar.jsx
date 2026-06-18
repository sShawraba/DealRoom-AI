import { Link } from 'react-router-dom';

export default function Topbar({ title, breadcrumbs = [] }) {
  return (
    <header className="h-14 border-b border-gray-200 bg-white flex items-center px-6 gap-2 text-sm text-gray-500">
      {breadcrumbs.map((b, i) => (
        <span key={i} className="flex items-center gap-2">
          {b.to ? (
            <Link to={b.to} className="hover:text-gray-900 transition-colors">
              {b.label}
            </Link>
          ) : (
            <span className="text-gray-900 font-medium">{b.label}</span>
          )}
          {i < breadcrumbs.length - 1 && <span>/</span>}
        </span>
      ))}
      {breadcrumbs.length === 0 && <span className="text-gray-900 font-medium">{title}</span>}
    </header>
  );
}
