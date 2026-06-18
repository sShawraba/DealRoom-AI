import { NavLink, useNavigate } from 'react-router-dom';
import useAuthStore from '../../store/authStore';

const links = [
  { to: '/', label: 'Dashboard', icon: '⬛' },
  { to: '/audit', label: 'Audit Log', icon: '📋' },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="w-56 min-h-screen bg-gray-900 text-white flex flex-col">
      <div className="px-5 py-4 border-b border-gray-700">
        <p className="text-xs text-gray-400 uppercase tracking-wider">DealRoom AI</p>
        <p className="mt-1 text-sm font-semibold truncate">{user?.firm_name ?? user?.tenant_name ?? 'Workspace'}</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            <span>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-gray-700">
        <p className="text-xs text-gray-400 truncate mb-2">{user?.email ?? ''}</p>
        <button
          onClick={handleLogout}
          className="w-full text-left text-sm text-gray-300 hover:text-white transition-colors"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
