import { RISK_COLORS } from '../deal-rooms/DealRoomCard';

function ShapBar({ factor, maxMagnitude }) {
  const width = maxMagnitude > 0 ? (factor.magnitude / maxMagnitude) * 100 : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs w-24 truncate text-gray-600" title={factor.feature}>{factor.feature}</span>
      <div
        className={`h-3 rounded flex-1 max-w-32 ${factor.direction === 'increases_risk' ? 'bg-red-400' : 'bg-green-400'}`}
        style={{ width: `${width}%` }}
      />
      <span className="text-xs text-gray-500 w-4">{factor.direction === 'increases_risk' ? '↑' : '↓'}</span>
    </div>
  );
}

export default function RiskScoreCard({ report }) {
  const tier = report?.risk_tier ?? 'null';
  const colors = RISK_COLORS[tier] ?? RISK_COLORS.null;
  const shapFactors = report?.shap_factors ?? report?.top_shap_factors ?? [];
  const maxMag = Math.max(...shapFactors.map((f) => f.magnitude ?? 0), 0.001);

  return (
    <div className={`rounded-xl border-2 ${colors.border} ${colors.bg} p-5`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900 text-sm">Risk Score</h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${colors.badge} ${colors.text} capitalize`}>
          {tier}
        </span>
      </div>

      <p className={`text-4xl font-bold ${colors.text} mb-1`}>
        {report?.risk_score ?? '—'}
        {report?.risk_score != null && <span className="text-base font-normal text-gray-400 ml-1">/ 100</span>}
      </p>

      {shapFactors.length > 0 && (
        <div className="mt-4 space-y-2">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Top factors</p>
          {shapFactors.slice(0, 3).map((f, i) => (
            <ShapBar key={i} factor={f} maxMagnitude={maxMag} />
          ))}
        </div>
      )}
    </div>
  );
}
