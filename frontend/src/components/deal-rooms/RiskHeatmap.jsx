import DealRoomCard from './DealRoomCard';

const C = {
  cream:     '#FAF9F5',
  creamDark: '#E8E2D0',
  taupe:     '#B8AF9C',
  ink:       '#14211A',
  green:     '#1A5E3A',
  gold:      '#D4A84B',
};

const TIER_META = [
  { key: 'low',      label: 'Low',      color: '#22c55e' },
  { key: 'medium',   label: 'Medium',   color: '#eab308' },
  { key: 'high',     label: 'High',     color: '#f97316' },
  { key: 'critical', label: 'Critical', color: '#ef4444' },
];

function RiskDonut({ rooms }) {
  const counts = { low: 0, medium: 0, high: 0, critical: 0 };
  rooms.forEach(r => { if (r.risk_tier && r.risk_tier in counts) counts[r.risk_tier]++; });
  const tiered = Object.values(counts).reduce((a, b) => a + b, 0);

  const R = 36, cx = 50, cy = 50;
  const circ = 2 * Math.PI * R;

  let cumOffset = 0;
  const segments = TIER_META.map(({ key, color }) => {
    const count = counts[key];
    const len = tiered > 0 ? (count / tiered) * circ : 0;
    const offset = cumOffset;
    cumOffset += len;
    return { key, color, len, offset, count };
  }).filter(s => s.len > 0);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <svg width="96" height="96" viewBox="0 0 100 100" style={{ flexShrink: 0 }}>
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={C.creamDark} strokeWidth="11" />
        {segments.map(s => (
          <circle
            key={s.key}
            cx={cx} cy={cy} r={R}
            fill="none"
            stroke={s.color}
            strokeWidth="11"
            strokeDasharray={`${s.len} ${circ}`}
            strokeDashoffset={-s.offset}
            transform="rotate(-90 50 50)"
          />
        ))}
        <text x={cx} y={cy - 3} textAnchor="middle" fontSize="16" fontWeight="800" fill={C.ink} fontFamily="Georgia, serif">
          {rooms.length}
        </text>
        <text x={cx} y={cy + 11} textAnchor="middle" fontSize="7.5" fill={C.taupe} fontWeight="700" letterSpacing="0.5">
          DEALS
        </text>
      </svg>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 5, minWidth: 110 }}>
        {TIER_META.map(({ key, label, color }) => (
          <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: color, flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: C.taupe, flex: 1 }}>{label}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: C.ink }}>{counts[key]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatBadge({ value, label }) {
  return (
    <div style={{
      background: '#fff',
      border: `1px solid ${C.creamDark}`,
      borderRadius: 10,
      padding: '12px 16px',
      textAlign: 'center',
      minWidth: 88,
    }}>
      <div style={{
        fontSize: 22, fontWeight: 800, color: C.green,
        letterSpacing: -1, lineHeight: 1,
        fontFamily: "Georgia, 'Times New Roman', serif",
      }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: C.taupe, marginTop: 4, fontWeight: 500 }}>{label}</div>
    </div>
  );
}

export default function RiskHeatmap({ rooms }) {
  if (!rooms || rooms.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-4xl mb-3">📂</p>
        <p className="text-sm">No deal rooms yet. Create one to get started.</p>
      </div>
    );
  }

  const scored = rooms.filter(r => r.risk_score != null);
  const avgScore = scored.length > 0
    ? Math.round(scored.reduce((s, r) => s + r.risk_score, 0) / scored.length)
    : null;
  const atRisk = rooms.filter(r => r.risk_tier === 'critical' || r.risk_tier === 'high').length;
  const totalDocs = rooms.reduce((s, r) => s + (r.document_count ?? 0), 0);
  const disputed = rooms.reduce((s, r) => s + (r.unresolved_annotations ?? 0), 0);

  return (
    <div>
      {/* Portfolio Analytics Strip */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 20,
        alignItems: 'center',
        background: C.cream,
        border: `1px solid ${C.creamDark}`,
        borderRadius: 16,
        padding: '20px 24px',
        marginBottom: 24,
        boxShadow: '0 2px 12px rgba(20,33,26,0.04)',
      }}>
        <div>
          <p style={{ fontSize: 10, fontWeight: 700, color: C.gold, letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 10 }}>
            Risk Distribution
          </p>
          <RiskDonut rooms={rooms} />
        </div>

        <div style={{ width: 1, alignSelf: 'stretch', background: C.creamDark, flexShrink: 0, margin: '4px 0' }} />

        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: C.gold, letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 10 }}>
            Portfolio Stats
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {avgScore != null && <StatBadge value={avgScore} label="avg risk score" />}
            <StatBadge value={atRisk} label="at-risk deals" />
            <StatBadge value={totalDocs} label="total docs" />
            {disputed > 0 && <StatBadge value={disputed} label="disputed" />}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {rooms.map((room) => (
          <DealRoomCard key={room.id} room={room} />
        ))}
      </div>
    </div>
  );
}
