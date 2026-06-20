import { NavLink, useNavigate } from 'react-router-dom';
import useAuthStore from '../../store/authStore';

const ALL_LINKS = [
  { to: '/dashboard', label: 'Dashboard', icon: '▦', adminOnly: false },
  { to: '/audit',     label: 'Audit Log', icon: '◈', adminOnly: true  },
];

// Miniature version of the split-page icon from the logo
function PageIcon() {
  return (
    <svg width="26" height="33" viewBox="0 0 160 200" fill="none" aria-hidden>
      <rect x="0"  y="0" width="75"  height="200" rx="12" fill="#E8E2D0"/>
      <rect x="85" y="0" width="75"  height="200" rx="12" fill="#1A5E3A"/>
      <line x1="14" y1="36"  x2="62"  y2="36"  stroke="#B8AF9C" strokeWidth="7" strokeLinecap="round"/>
      <line x1="14" y1="60"  x2="52"  y2="60"  stroke="#B8AF9C" strokeWidth="7" strokeLinecap="round"/>
      <line x1="14" y1="84"  x2="64"  y2="84"  stroke="#B8AF9C" strokeWidth="7" strokeLinecap="round"/>
      <line x1="14" y1="108" x2="42"  y2="108" stroke="#B8AF9C" strokeWidth="7" strokeLinecap="round"/>
      <line x1="99" y1="36"  x2="148" y2="36"  stroke="#FAF9F5" strokeWidth="7.5" strokeLinecap="round"/>
      <line x1="99" y1="60"  x2="130" y2="60"  stroke="#FAF9F5" strokeWidth="7.5" strokeLinecap="round" opacity="0.6"/>
      <line x1="99" y1="84"  x2="146" y2="84"  stroke="#FAF9F5" strokeWidth="7.5" strokeLinecap="round" opacity="0.6"/>
      <circle cx="122" cy="148" r="22" fill="none" stroke="#D4A84B" strokeWidth="7"/>
      <path d="M110 148 L119 158 L137 135" fill="none" stroke="#D4A84B" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const links = ALL_LINKS.filter((l) => !l.adminOnly || user?.role === 'admin');

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="w-56 min-h-screen flex flex-col" style={{ background: '#14211A' }}>

      {/* Logo + firm */}
      <div className="px-4 py-5 flex flex-col gap-3" style={{ borderBottom: '1px solid rgba(232,226,208,0.12)' }}>
        <div className="flex items-center gap-2.5">
          <PageIcon />
          <span style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontWeight: 700, fontSize: 14, color: '#FAF9F5', letterSpacing: -0.3,
          }}>
            DealRoom <span style={{ color: '#D4A84B', fontWeight: 400 }}>AI</span>
          </span>
        </div>
        <p className="text-xs truncate" style={{ color: '#B8AF9C' }}>
          {user?.firm_name ?? user?.tenant_name ?? 'Workspace'}
        </p>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/dashboard'}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 12px', borderRadius: 9,
              fontSize: 13, fontWeight: isActive ? 600 : 400,
              textDecoration: 'none',
              color:      isActive ? '#FAF9F5' : 'rgba(248,244,236,0.55)',
              background: isActive ? '#1A5E3A' : 'transparent',
              transition: 'all 0.15s',
            })}
          >
            <span style={{ fontSize: 12 }}>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User + sign out */}
      <div className="px-4 py-4" style={{ borderTop: '1px solid rgba(232,226,208,0.12)' }}>
        <p className="text-xs truncate mb-3" style={{ color: '#B8AF9C' }}>{user?.email ?? ''}</p>
        <button
          onClick={handleLogout}
          className="w-full text-left text-sm transition-colors"
          style={{ color: 'rgba(248,244,236,0.45)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          onMouseEnter={(e) => { e.target.style.color = '#FAF9F5'; }}
          onMouseLeave={(e) => { e.target.style.color = 'rgba(248,244,236,0.45)'; }}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
