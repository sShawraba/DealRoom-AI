import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../api/auth';
import useAuthStore from '../store/authStore';

const C = {
  cream:     '#FAF9F5',
  creamMid:  '#F2EDE3',
  creamDark: '#E8E2D0',
  taupe:     '#B8AF9C',
  ink:       '#14211A',
  green:     '#1A5E3A',
  gold:      '#D4A84B',
};

function PageIcon({ size = 60, dark = false }) {
  const h = Math.round(size * 200 / 160);
  return (
    <svg width={size} height={h} viewBox="0 0 160 200" fill="none" aria-hidden>
      <rect x="0"  y="0" width="75"  height="200" rx="12" fill={dark ? 'rgba(255,255,255,0.08)' : C.creamDark}/>
      <rect x="85" y="0" width="75"  height="200" rx="12" fill={dark ? 'rgba(255,255,255,0.14)' : C.green}/>
      <line x1="14" y1="36"  x2="62"  y2="36"  stroke={dark ? 'rgba(255,255,255,0.25)' : C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="60"  x2="52"  y2="60"  stroke={dark ? 'rgba(255,255,255,0.25)' : C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="84"  x2="64"  y2="84"  stroke={dark ? 'rgba(255,255,255,0.25)' : C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="108" x2="42"  y2="108" stroke={dark ? 'rgba(255,255,255,0.25)' : C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="132" x2="58"  y2="132" stroke={dark ? 'rgba(255,255,255,0.25)' : C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="99" y1="36"  x2="148" y2="36"  stroke={dark ? 'rgba(255,255,255,0.65)' : C.cream} strokeWidth="7"   strokeLinecap="round"/>
      <line x1="99" y1="60"  x2="130" y2="60"  stroke={dark ? 'rgba(255,255,255,0.4)'  : C.cream} strokeWidth="7"   strokeLinecap="round" opacity="0.6"/>
      <line x1="99" y1="84"  x2="146" y2="84"  stroke={dark ? 'rgba(255,255,255,0.4)'  : C.cream} strokeWidth="7"   strokeLinecap="round" opacity="0.6"/>
      <circle cx="122" cy="148" r="22" fill="none" stroke={C.gold} strokeWidth="6"/>
      <path d="M110 148 L119 158 L137 135" fill="none" stroke={C.gold} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ── Marketing panel ──────────────────────────────────────────────────────────

const MOCK_TIERS = [
  { key: 'low',      label: 'Low Risk',      color: '#22c55e', pct: 0.42 },
  { key: 'medium',   label: 'Medium Risk',   color: '#eab308', pct: 0.29 },
  { key: 'high',     label: 'High Risk',     color: '#f97316', pct: 0.20 },
  { key: 'critical', label: 'Critical Risk', color: '#ef4444', pct: 0.09 },
];
const MOCK_TOTAL = 24;

function MockDonut() {
  const R = 52, cx = 70, cy = 70;
  const circ = 2 * Math.PI * R;

  let cumOffset = 0;
  const segments = MOCK_TIERS.map(t => {
    const len = t.pct * circ;
    const offset = cumOffset;
    cumOffset += len;
    return { ...t, len, offset };
  });

  return (
    <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
      <svg width="140" height="140" viewBox="0 0 140 140" style={{ flexShrink: 0 }}>
        <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(0,0,0,0.15)" strokeWidth="18" />
        {segments.map(s => (
          <circle
            key={s.key}
            cx={cx} cy={cy} r={R}
            fill="none"
            stroke={s.color}
            strokeWidth="14"
            strokeDasharray={`${s.len} ${circ}`}
            strokeDashoffset={-s.offset}
            transform={`rotate(-90 ${cx} ${cy})`}
          />
        ))}
        <text x={cx} y={cy - 5} textAnchor="middle" fontSize="24" fontWeight="800" fill="white" fontFamily="Georgia, serif">
          {MOCK_TOTAL}
        </text>
        <text x={cx} y={cy + 13} textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.45)" fontWeight="700" letterSpacing="1">
          DEALS
        </text>
      </svg>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
        {MOCK_TIERS.map(t => (
          <div key={t.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 9, height: 9, borderRadius: 2, background: t.color, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', flex: 1 }}>{t.label}</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'white', minWidth: 24, textAlign: 'right' }}>
              {Math.round(t.pct * MOCK_TOTAL)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricBar({ label, displayValue, pct, color }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 5 }}>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 12, color, fontWeight: 700 }}>{displayValue}</span>
      </div>
      <div style={{ height: 4, borderRadius: 3, background: 'rgba(0,0,0,0.15)', overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`, borderRadius: 3,
          background: color,
          boxShadow: `0 0 8px ${color}55`,
        }} />
      </div>
    </div>
  );
}

function MarketingPanel() {
  return (
    <div style={{
      flex: '0 0 44%',
      maxWidth: 540,
      background: C.green,
      padding: '48px 44px',
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      height: '100vh',
      overflow: 'hidden',
    }}>
      {/* Gold top accent */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, ${C.gold}, transparent)`,
      }} />

      {/* Subtle radial accent */}
      <div style={{
        position: 'absolute', top: -120, right: -120,
        width: 400, height: 400, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(255,255,255,0.07) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 44 }}>
        <PageIcon size={30} dark />
        <span style={{
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontWeight: 700, fontSize: 18, color: C.cream, letterSpacing: -0.4,
        }}>
          DealRoom <span style={{ color: C.gold, fontWeight: 400 }}>AI</span>
        </span>
      </div>

      {/* Headline */}
      <h2 style={{
        fontFamily: "Georgia, 'Times New Roman', serif",
        fontSize: 30, fontWeight: 800, color: 'white',
        lineHeight: 1.15, letterSpacing: -0.8, marginBottom: 6,
      }}>
        Intelligence for<br />every deal.
      </h2>
      <div style={{ width: 40, height: 2, background: C.gold, marginBottom: 32 }} />

      {/* Donut chart panel */}
      <div style={{
        background: 'rgba(0,0,0,0.12)',
        borderRadius: 14,
        border: '1px solid rgba(255,255,255,0.12)',
        padding: '18px 22px',
        marginBottom: 16,
      }}>
        <p style={{
          fontSize: 9, fontWeight: 700, color: C.gold,
          letterSpacing: 1.8, textTransform: 'uppercase', marginBottom: 16,
        }}>
          Portfolio Risk Overview · Illustrative
        </p>
        <MockDonut />
      </div>

      {/* Metric bars panel */}
      <div style={{
        background: 'rgba(0,0,0,0.12)',
        borderRadius: 14,
        border: '1px solid rgba(255,255,255,0.12)',
        padding: '18px 22px',
        marginBottom: 'auto',
      }}>
        <p style={{
          fontSize: 9, fontWeight: 700, color: C.gold,
          letterSpacing: 1.8, textTransform: 'uppercase', marginBottom: 16,
        }}>
          Platform Capabilities
        </p>
        <MetricBar label="Documents analyzed"  displayValue="2,847" pct={95} color="#22c55e" />
        <MetricBar label="Risks auto-detected" displayValue="94%"   pct={94} color={C.gold} />
        <MetricBar label="Audit completeness"  displayValue="100%"  pct={100} color="#60a5fa" />
      </div>

      <p style={{ marginTop: 26, fontSize: 12, color: 'rgba(255,255,255,0.28)', lineHeight: 1.6 }}>
        Trusted by investment professionals to close with confidence.
      </p>
    </div>
  );
}

// ── Form ─────────────────────────────────────────────────────────────────────

const inputStyle = {
  width: '100%', border: `1.5px solid ${C.creamDark}`,
  borderRadius: 10, padding: '11px 14px', fontSize: 14,
  outline: 'none', background: '#fff',
  boxSizing: 'border-box', color: C.ink,
  transition: 'border-color 0.15s',
  fontFamily: 'inherit',
};

function Field({ label, children }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 700, color: C.ink, letterSpacing: 0.3, textTransform: 'uppercase', marginBottom: 7 }}>
        {label}
      </label>
      {children}
    </div>
  );
}

export default function Register() {
  const navigate = useNavigate();
  const { setAuth, token } = useAuthStore();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', tenant_name: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [wide, setWide] = useState(() => typeof window !== 'undefined' && window.innerWidth >= 860);

  useEffect(() => {
    if (token) navigate('/dashboard', { replace: true });
  }, [token, navigate]);

  useEffect(() => {
    const h = () => setWide(window.innerWidth >= 860);
    window.addEventListener('resize', h, { passive: true });
    return () => window.removeEventListener('resize', h);
  }, []);

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await register(form);
      setAuth(data.access_token, data.user ?? null);
      navigate('/dashboard');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : (detail ?? 'Registration failed.'));
    } finally {
      setLoading(false);
    }
  };

  const focusGreen = (e) => { e.target.style.borderColor = C.green; };
  const blurReset  = (e) => { e.target.style.borderColor = C.creamDark; };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    }}>
      {wide && <MarketingPanel />}

      {/* Form side */}
      <div style={{
        flex: 1,
        background: C.creamMid,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        minHeight: '100vh',
      }}>
        <div style={{ width: '100%', maxWidth: 480, marginBottom: 20 }}>
          <Link to="/" style={{ color: C.taupe, fontSize: 13, textDecoration: 'none' }}>
            ← Back to home
          </Link>
        </div>

        <div style={{
          width: '100%', maxWidth: 480,
          background: C.cream,
          borderRadius: 18,
          border: `1px solid ${C.creamDark}`,
          boxShadow: '0 8px 40px rgba(20,33,26,0.09)',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '32px 36px 24px',
            borderBottom: `1px solid ${C.creamDark}`,
            textAlign: 'center',
            background: '#fff',
            display: 'flex', flexDirection: 'column', alignItems: 'center',
          }}>
            <PageIcon size={60} />
            <div style={{ width: 100, height: 1, background: C.gold, marginTop: 18 }} />
          </div>

          <div style={{ padding: '30px 36px 36px' }}>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: C.ink, letterSpacing: -0.4, marginBottom: 4 }}>
              Register your firm
            </h1>
            <p style={{ color: C.taupe, fontSize: 14, marginBottom: 26 }}>
              Set up your AI-powered deal workspace in seconds
            </p>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
              {error && (
                <div style={{
                  background: '#fef2f2', border: '1px solid #fca5a5',
                  color: '#b91c1c', borderRadius: 9, padding: '11px 14px', fontSize: 13,
                }}>
                  {error}
                </div>
              )}

              <Field label="Your full name">
                <input type="text" name="full_name" value={form.full_name}
                  onChange={handleChange} required placeholder="Jane Smith"
                  style={inputStyle} onFocus={focusGreen} onBlur={blurReset} />
              </Field>

              <Field label="Work email">
                <input type="email" name="email" value={form.email}
                  onChange={handleChange} required placeholder="you@firm.com"
                  style={inputStyle} onFocus={focusGreen} onBlur={blurReset} />
              </Field>

              <Field label="Firm name">
                <input type="text" name="tenant_name" value={form.tenant_name}
                  onChange={handleChange} required placeholder="Acme Capital"
                  style={inputStyle} onFocus={focusGreen} onBlur={blurReset} />
              </Field>

              <Field label="Password">
                <input type="password" name="password" value={form.password}
                  onChange={handleChange} required minLength={8} placeholder="Min. 8 characters"
                  style={inputStyle} onFocus={focusGreen} onBlur={blurReset} />
              </Field>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%', background: loading ? '#2d7a52' : C.green,
                  color: C.cream, fontWeight: 700, fontSize: 15,
                  padding: '13px', borderRadius: 10, border: 'none',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.8 : 1,
                  marginTop: 4, letterSpacing: -0.2,
                  transition: 'opacity 0.15s',
                  fontFamily: 'inherit',
                }}
              >
                {loading ? 'Creating workspace…' : 'Create Account →'}
              </button>

              <p style={{ textAlign: 'center', color: C.taupe, fontSize: 12, marginTop: -4 }}>
                Free to start · No credit card required
              </p>
            </form>

            <div style={{ marginTop: 22, paddingTop: 20, borderTop: `1px solid ${C.creamDark}`, textAlign: 'center' }}>
              <p style={{ color: C.taupe, fontSize: 14 }}>
                Already a member?{' '}
                <Link to="/login" style={{ color: C.green, fontWeight: 700, textDecoration: 'none' }}>
                  Sign in here →
                </Link>
              </p>
            </div>
          </div>
        </div>

        <p style={{ color: C.taupe, fontSize: 12, marginTop: 28, opacity: 0.7 }}>
          © 2026 DealRoom AI. All rights reserved.
        </p>
      </div>
    </div>
  );
}
