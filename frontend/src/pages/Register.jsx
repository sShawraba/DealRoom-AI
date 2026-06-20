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

function PageIcon({ size = 60 }) {
  const h = Math.round(size * 200 / 160);
  return (
    <svg width={size} height={h} viewBox="0 0 160 200" fill="none" aria-hidden>
      <rect x="0"  y="0" width="75"  height="200" rx="12" fill={C.creamDark}/>
      <rect x="85" y="0" width="75"  height="200" rx="12" fill={C.green}/>
      <line x1="14" y1="36"  x2="62"  y2="36"  stroke={C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="60"  x2="52"  y2="60"  stroke={C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="84"  x2="64"  y2="84"  stroke={C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="108" x2="42"  y2="108" stroke={C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="132" x2="58"  y2="132" stroke={C.taupe} strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="99" y1="36"  x2="148" y2="36"  stroke={C.cream} strokeWidth="7"   strokeLinecap="round"/>
      <line x1="99" y1="60"  x2="130" y2="60"  stroke={C.cream} strokeWidth="7"   strokeLinecap="round" opacity="0.6"/>
      <line x1="99" y1="84"  x2="146" y2="84"  stroke={C.cream} strokeWidth="7"   strokeLinecap="round" opacity="0.6"/>
      <circle cx="122" cy="148" r="22" fill="none" stroke={C.gold} strokeWidth="6"/>
      <path d="M110 148 L119 158 L137 135" fill="none" stroke={C.gold} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

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

  useEffect(() => {
    if (token) navigate('/dashboard', { replace: true });
  }, [token, navigate]);

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
      background: C.creamMid,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '24px',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    }}>

      {/* Back link */}
      <div style={{ width: '100%', maxWidth: 480, marginBottom: 20 }}>
        <Link to="/" style={{ color: C.taupe, fontSize: 13, textDecoration: 'none' }}>
          ← Back to home
        </Link>
      </div>

      {/* Card */}
      <div style={{
        width: '100%', maxWidth: 480,
        background: C.cream,
        borderRadius: 18,
        border: `1px solid ${C.creamDark}`,
        boxShadow: '0 8px 40px rgba(20,33,26,0.09)',
        overflow: 'hidden',
      }}>
        {/* Icon-only header — no wordmark text */}
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

        {/* Form area */}
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
  );
}
