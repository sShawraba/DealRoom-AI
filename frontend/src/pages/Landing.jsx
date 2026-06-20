import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';

// Exact colors extracted from the logo SVG
const C = {
  cream:     '#FAF9F5',  // logo background — page base
  creamMid:  '#F2EDE3',  // warm mid-cream for alt sections
  creamDark: '#E8E2D0',  // left-page color in logo — borders
  taupe:     '#B8AF9C',  // logo line strokes — muted text
  ink:       '#14211A',  // wordmark color — headings & body text
  green:     '#1A5E3A',  // right page / "AI" label — brand green
  greenDark: '#123D26',  // darker green for hovers
  gold:      '#D4A84B',  // checkmark & rule in logo — accent
};

// Inline icon: mirrors the split-page mark from the logo
function PageIcon({ size = 34 }) {
  const h = Math.round(size * 200 / 160);
  return (
    <svg width={size} height={h} viewBox="0 0 160 200" fill="none" aria-hidden>
      <rect x="0"  y="0" width="75"  height="200" rx="12" fill={C.creamDark}/>
      <rect x="85" y="0" width="75"  height="200" rx="12" fill={C.green}/>
      <line x1="14" y1="36"  x2="62"  y2="36"  stroke={C.taupe}   strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="60"  x2="52"  y2="60"  stroke={C.taupe}   strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="84"  x2="64"  y2="84"  stroke={C.taupe}   strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="108" x2="42"  y2="108" stroke={C.taupe}   strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="14" y1="132" x2="58"  y2="132" stroke={C.taupe}   strokeWidth="6.5" strokeLinecap="round"/>
      <line x1="99" y1="36"  x2="148" y2="36"  stroke={C.cream}   strokeWidth="7"   strokeLinecap="round"/>
      <line x1="99" y1="60"  x2="130" y2="60"  stroke={C.cream}   strokeWidth="7"   strokeLinecap="round" opacity="0.6"/>
      <line x1="99" y1="84"  x2="146" y2="84"  stroke={C.cream}   strokeWidth="7"   strokeLinecap="round" opacity="0.6"/>
      <circle cx="122" cy="148" r="22" fill="none" stroke={C.gold} strokeWidth="6"/>
      <path d="M110 148 L119 158 L137 135" fill="none" stroke={C.gold} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function NavLogo() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
      <PageIcon size={28} />
      <span style={{
        fontFamily: "Georgia, 'Times New Roman', serif",
        fontWeight: 700, fontSize: 19, color: C.ink, letterSpacing: -0.5,
      }}>
        DealRoom <span style={{ color: C.green, fontWeight: 400 }}>AI</span>
      </span>
    </div>
  );
}

const FEATURES = [
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={C.cream} strokeWidth="2" strokeLinecap="round">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/>
        <line x1="9" y1="14" x2="15" y2="14"/><line x1="9" y1="18" x2="13" y2="18"/>
      </svg>
    ),
    title: 'AI Document Intelligence',
    body: 'Upload financials, contracts, and data rooms. Our AI extracts key clauses, flags risks, and surfaces critical insights in seconds — not days.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={C.cream} strokeWidth="2" strokeLinecap="round">
        <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
      </svg>
    ),
    title: 'Secure Deal Rooms',
    body: 'Invite partners with precision access controls. Every view, download, and annotation is logged. Complete audit trail, every time.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={C.cream} strokeWidth="2" strokeLinecap="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    ),
    title: 'Executive-Ready Reports',
    body: 'From raw documents to boardroom-ready risk summaries at the click of a button. Consistent, comprehensive, and ready to present.',
  },
];

const STATS = [
  { stat: '10×',     label: 'Faster analysis'   },
  { stat: '100%',    label: 'Audit coverage'     },
  { stat: '< 2 min', label: 'First insight'      },
  { stat: '∞',       label: 'Documents per room' },
];

export default function Landing() {
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    if (token) navigate('/dashboard', { replace: true });
  }, [token, navigate]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div style={{
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      color: C.ink, background: C.cream,
    }}>

      {/* ── NAVBAR ── */}
      <header style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 50,
        background: scrolled ? `rgba(250,249,245,0.97)` : 'rgba(250,249,245,0.85)',
        backdropFilter: 'blur(14px)',
        borderBottom: scrolled ? `1px solid ${C.creamDark}` : '1px solid transparent',
        transition: 'all 0.25s ease',
      }}>
        <div style={{
          maxWidth: 1200, margin: '0 auto', padding: '0 28px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 68,
        }}>
          <Link to="/" style={{ textDecoration: 'none' }}>
            <NavLogo />
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <Link to="/login" style={{ color: C.ink, fontSize: 14, fontWeight: 500, textDecoration: 'none', opacity: 0.75 }}>
              Sign In
            </Link>
            <Link to="/register" style={{
              background: C.green, color: C.cream,
              fontSize: 14, fontWeight: 600,
              padding: '9px 22px', borderRadius: 8, textDecoration: 'none',
              letterSpacing: -0.1,
            }}>
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section style={{
        minHeight: '100vh',
        background: `linear-gradient(160deg, ${C.cream} 0%, ${C.creamMid} 100%)`,
        display: 'flex', alignItems: 'center',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Decorative ring accents */}
        <div style={{ position: 'absolute', top: '8%', right: '-6%', width: 560, height: 560, borderRadius: '50%', border: `1px solid rgba(212,168,75,0.18)`, pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', top: '18%', right: '2%',  width: 360, height: 360, borderRadius: '50%', border: `1px solid rgba(212,168,75,0.1)`,  background: 'rgba(212,168,75,0.02)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', bottom: '-12%', left: '-4%', width: 400, height: 400, borderRadius: '50%', border: `1px solid ${C.creamDark}`, pointerEvents: 'none' }} />

        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '148px 28px 100px', width: '100%' }}>
          <div style={{ maxWidth: 700 }}>

            {/* Headline */}
            <h1 style={{
              fontSize: 'clamp(46px, 6.8vw, 86px)',
              fontWeight: 800, lineHeight: 1.03,
              letterSpacing: '-2.5px', color: C.ink,
              fontFamily: "Georgia, 'Times New Roman', serif",
              margin: 0,
            }}>
              Due Diligence.<br />
              <span style={{ color: C.green }}>Redefined.</span>
            </h1>

            {/* Gold rule — matches the logo */}
            <div style={{ width: 220, height: 1.5, background: C.gold, margin: '26px 0 30px' }} />

            {/* Subtext */}
            <p style={{
              fontSize: 'clamp(16px, 1.9vw, 19px)',
              lineHeight: 1.72, color: '#5a5040',
              marginBottom: 46, maxWidth: 540,
            }}>
              Transform thousands of pages into actionable intelligence —
              in hours, not weeks. Built for the most demanding investment professionals.
            </p>

            {/* CTAs */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, marginBottom: 30 }}>
              <Link to="/register" style={{
                background: C.green, color: C.cream,
                fontWeight: 700, fontSize: 16,
                padding: '14px 36px', borderRadius: 10,
                textDecoration: 'none', letterSpacing: -0.2,
                boxShadow: '0 4px 18px rgba(26,94,58,0.22)',
              }}>
                Register Your Firm →
              </Link>
              <a href="#features" style={{
                border: `1.5px solid ${C.creamDark}`,
                color: C.ink, fontWeight: 500, fontSize: 16,
                padding: '14px 36px', borderRadius: 10,
                textDecoration: 'none', background: 'transparent',
              }}>
                See How It Works
              </a>
            </div>

            <p style={{ color: C.taupe, fontSize: 13 }}>
              Already a member?{' '}
              <Link to="/login" style={{ color: C.green, textDecoration: 'none', fontWeight: 600 }}>
                Sign in here
              </Link>
            </p>
          </div>
        </div>
      </section>

      {/* ── SLOGANS STRIP ── */}
      <div style={{
        background: C.cream,
        borderTop: `1px solid ${C.gold}`,
        borderBottom: `1px solid ${C.gold}`,
        padding: '15px 28px',
      }}>
        <div style={{
          maxWidth: 1200, margin: '0 auto',
          display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '10px 40px',
        }}>
          {[
            'From documents to decisions in hours, not weeks.',
            'The intelligence edge that closes more deals.',
            'Outpace competition with AI-accelerated analysis.',
          ].map((s) => (
            <span key={s} style={{ color: C.taupe, fontSize: 12, fontWeight: 600, letterSpacing: 0.5, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
              <span style={{ color: C.gold, marginRight: 8 }}>✦</span>{s}
            </span>
          ))}
        </div>
      </div>

      {/* ── FEATURES ── */}
      <section id="features" style={{ background: C.creamMid, padding: '96px 28px' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>

          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <p style={{ color: C.gold, fontWeight: 700, fontSize: 11, letterSpacing: 2.2, textTransform: 'uppercase', marginBottom: 14 }}>
              Built for professionals
            </p>
            <h2 style={{
              fontSize: 'clamp(28px, 4vw, 50px)', fontWeight: 800,
              color: C.ink, letterSpacing: '-1.5px',
              fontFamily: "Georgia, 'Times New Roman', serif",
              marginBottom: 16,
            }}>
              Everything your deal team needs
            </h2>
            <div style={{ width: 60, height: 1.5, background: C.gold, margin: '0 auto 20px' }} />
            <p style={{ color: '#6a5e52', fontSize: 17, lineHeight: 1.6, maxWidth: 440, margin: '0 auto' }}>
              One platform. End-to-end intelligence. No spreadsheets, no chaos.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 24 }}>
            {FEATURES.map((f) => (
              <div key={f.title} style={{
                background: '#fff', borderRadius: 16, padding: '36px 30px',
                border: `1px solid ${C.creamDark}`,
                boxShadow: '0 2px 20px rgba(20,33,26,0.05)',
              }}>
                <div style={{
                  width: 50, height: 50, borderRadius: 13,
                  background: C.green,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginBottom: 20,
                }}>
                  {f.icon}
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: C.ink, marginBottom: 12, letterSpacing: -0.3 }}>
                  {f.title}
                </h3>
                <p style={{ fontSize: 15, lineHeight: 1.68, color: '#6a5e52' }}>
                  {f.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── WHY SECTION ── */}
      <section style={{ background: C.cream, padding: '88px 28px' }}>
        <div style={{
          maxWidth: 1200, margin: '0 auto',
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: 64, alignItems: 'center',
        }}>
          <div>
            <p style={{ color: C.gold, fontWeight: 700, fontSize: 11, letterSpacing: 2.2, textTransform: 'uppercase', marginBottom: 14 }}>
              Why DealRoom AI
            </p>
            <h2 style={{
              fontSize: 'clamp(26px, 3.5vw, 44px)', fontWeight: 800,
              color: C.ink, letterSpacing: '-1.2px',
              fontFamily: "Georgia, 'Times New Roman', serif",
              marginBottom: 8,
            }}>
              Intelligence that moves at the speed of deals
            </h2>
            <div style={{ width: 60, height: 1.5, background: C.gold, margin: '16px 0 22px' }} />
            <p style={{ fontSize: 16, lineHeight: 1.78, color: '#6a5e52', marginBottom: 32 }}>
              Traditional due diligence is slow, expensive, and error-prone.
              DealRoom AI eliminates the bottlenecks — letting your team focus
              on the decisions that matter, not drowning in documents.
            </p>
            <Link to="/register" style={{
              display: 'inline-block',
              background: C.green, color: C.cream,
              fontWeight: 600, fontSize: 15,
              padding: '12px 28px', borderRadius: 9,
              textDecoration: 'none', letterSpacing: -0.2,
            }}>
              Start for free →
            </Link>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {STATS.map(({ stat, label }) => (
              <div key={label} style={{
                background: '#fff', borderRadius: 14, padding: '28px 20px', textAlign: 'center',
                border: `1px solid ${C.creamDark}`,
                boxShadow: '0 2px 12px rgba(20,33,26,0.04)',
              }}>
                <div style={{
                  fontSize: 30, fontWeight: 800, color: C.green,
                  letterSpacing: -1, lineHeight: 1,
                  fontFamily: "Georgia, 'Times New Roman', serif",
                }}>
                  {stat}
                </div>
                <div style={{ width: 28, height: 1, background: C.gold, margin: '10px auto 10px' }} />
                <div style={{ fontSize: 12, color: C.taupe, fontWeight: 600, letterSpacing: 0.3 }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ── */}
      <section style={{ background: C.creamMid, padding: '96px 28px' }}>
        <div style={{
          maxWidth: 680, margin: '0 auto', textAlign: 'center',
          background: '#fff',
          border: `1px solid ${C.creamDark}`,
          borderRadius: 20, padding: '56px 48px',
          boxShadow: '0 8px 40px rgba(20,33,26,0.07)',
          position: 'relative',
        }}>
          {/* Gold top accent rule */}
          <div style={{ position: 'absolute', top: 0, left: '15%', right: '15%', height: 2, background: C.gold, borderRadius: 1 }} />

          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 28 }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: C.gold, display: 'block' }} />
            <span style={{ color: C.taupe, fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase' }}>
              For Investment Professionals
            </span>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: C.gold, display: 'block' }} />
          </div>

          <h2 style={{
            fontSize: 'clamp(26px, 4vw, 44px)', fontWeight: 800,
            color: C.ink, letterSpacing: '-1.5px', lineHeight: 1.1,
            fontFamily: "Georgia, 'Times New Roman', serif",
            marginBottom: 16,
          }}>
            Ready to transform<br />your deal flow?
          </h2>
          <div style={{ width: 60, height: 1.5, background: C.gold, margin: '0 auto 22px' }} />
          <p style={{ fontSize: 17, color: '#6a5e52', marginBottom: 40, lineHeight: 1.65 }}>
            Join investment professionals who use DealRoom AI to close with confidence.
            Register your firm today — it's free to start.
          </p>

          <Link to="/register" style={{
            display: 'inline-block',
            background: C.green, color: C.cream,
            fontWeight: 700, fontSize: 17,
            padding: '15px 44px', borderRadius: 12,
            textDecoration: 'none', letterSpacing: -0.3,
            boxShadow: '0 4px 20px rgba(26,94,58,0.2)',
            marginBottom: 22,
          }}>
            Register Your Firm →
          </Link>

          <p style={{ color: C.taupe, fontSize: 14 }}>
            Already a member?{' '}
            <Link to="/login" style={{ color: C.green, textDecoration: 'none', fontWeight: 700 }}>
              Sign in here
            </Link>
          </p>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ background: C.ink, padding: '36px 28px', borderTop: `2px solid ${C.gold}` }}>
        <div style={{
          maxWidth: 1200, margin: '0 auto',
          display: 'flex', flexWrap: 'wrap',
          alignItems: 'center', justifyContent: 'space-between', gap: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
            <PageIcon size={28} />
            <span style={{
              fontFamily: "Georgia, 'Times New Roman', serif",
              fontWeight: 700, fontSize: 17, color: C.cream, letterSpacing: -0.5,
            }}>
              DealRoom <span style={{ color: C.gold, fontWeight: 400 }}>AI</span>
            </span>
          </div>
          <p style={{ color: C.taupe, fontSize: 13 }}>
            © 2026 DealRoom AI. All rights reserved.
          </p>
          <div style={{ display: 'flex', gap: 24 }}>
            <Link to="/login"    style={{ color: C.taupe, fontSize: 13, textDecoration: 'none' }}>Sign In</Link>
            <Link to="/register" style={{ color: C.taupe, fontSize: 13, textDecoration: 'none' }}>Register</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
