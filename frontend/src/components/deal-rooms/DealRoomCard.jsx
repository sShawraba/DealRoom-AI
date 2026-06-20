import { Link } from 'react-router-dom';

const RISK_COLORS = {
  low:      { border: 'border-green-400',  bg: 'bg-green-50',  text: 'text-green-700',  badge: 'bg-green-100' },
  medium:   { border: 'border-yellow-400', bg: 'bg-yellow-50', text: 'text-yellow-700', badge: 'bg-yellow-100' },
  high:     { border: 'border-orange-400', bg: 'bg-orange-50', text: 'text-orange-700', badge: 'bg-orange-100' },
  critical: { border: 'border-red-400',    bg: 'bg-red-50',    text: 'text-red-700',    badge: 'bg-red-100' },
  null:     { border: 'border-brand-sand',  bg: 'bg-brand-warm', text: 'text-brand-taupe', badge: 'bg-brand-sand' },
};

export { RISK_COLORS };

export default function DealRoomCard({ room }) {
  const tier = room.risk_tier ?? 'null';
  const colors = RISK_COLORS[tier] ?? RISK_COLORS.null;

  return (
    <Link
      to={`/deal-rooms/${room.id}`}
      className={`block rounded-xl border-2 ${colors.border} ${colors.bg} p-5 hover:shadow-md transition-shadow`}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-brand-ink text-sm leading-snug">{room.target_company}</h3>
        {tier !== 'null' && (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${colors.badge} ${colors.text} capitalize shrink-0`}>
            {tier}
          </span>
        )}
      </div>

      {room.risk_score != null && (
        <p className={`mt-2 text-2xl font-bold ${colors.text}`}>
          {room.risk_score}
          <span className="text-xs font-normal text-brand-taupe ml-1">/ 100</span>
        </p>
      )}

      <div className="mt-3 flex items-center gap-4 text-xs text-brand-taupe">
        <span>{room.document_count ?? 0} docs</span>
        {room.unresolved_annotations > 0 && (
          <span className="text-red-600 font-medium">{room.unresolved_annotations} disputed</span>
        )}
      </div>
    </Link>
  );
}
