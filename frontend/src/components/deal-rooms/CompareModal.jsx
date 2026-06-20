import { useState } from 'react';
import { compare } from '../../api/dealRooms';
import { RISK_COLORS } from './DealRoomCard';

function buildSummary(a, b) {
  const score = (r) => r.risk_score != null ? `a risk score of ${r.risk_score}/100` : 'no risk score available';
  const tier = (r) => r.risk_tier ?? 'unscored';
  const flags = (r) => r.red_flag_count === 1 ? '1 red flag' : `${r.red_flag_count} red flags`;

  let text = `${a.target_company} presents a ${tier(a)} risk profile (${score(a)}) with ${flags(a)}, `;
  text += `compared to ${b.target_company} at ${tier(b)} risk (${score(b)}) with ${flags(b)}. `;

  if (a.risk_score != null && b.risk_score != null) {
    const diff = Math.abs(a.risk_score - b.risk_score);
    const higher = a.risk_score > b.risk_score ? a.target_company : b.target_company;
    if (diff < 5) {
      text += `Both deals carry a similar risk profile. `;
    } else {
      text += `${higher} carries meaningfully higher financial risk (${diff}-point gap). `;
    }
  }

  if (a.top_findings?.length && b.top_findings?.length) {
    text += `Key finding for ${a.target_company}: "${a.top_findings[0]}". `;
    text += `Key finding for ${b.target_company}: "${b.top_findings[0]}".`;
  }

  return text;
}

function SideCard({ room }) {
  const tier = room.risk_tier ?? 'null';
  const colors = RISK_COLORS[tier] ?? RISK_COLORS.null;

  return (
    <div className={`flex-1 rounded-xl border-2 ${colors.border} ${colors.bg} p-5 space-y-3 min-w-0`}>
      <div>
        <h3 className="font-semibold text-gray-900 truncate">{room.target_company}</h3>
        <div className="flex items-end gap-2 mt-1">
          {room.risk_score != null && (
            <span className={`text-3xl font-bold ${colors.text}`}>{room.risk_score}</span>
          )}
          <span className={`text-sm capitalize font-medium ${colors.text} mb-0.5`}>{tier} risk</span>
        </div>
        <p className="text-xs text-gray-500 mt-1">{room.red_flag_count} red flag{room.red_flag_count !== 1 ? 's' : ''}</p>
      </div>

      {room.top_findings?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Key Findings</p>
          <ul className="space-y-1">
            {room.top_findings.map((f, i) => (
              <li key={i} className="text-xs text-gray-700 leading-snug line-clamp-3">• {f}</li>
            ))}
          </ul>
        </div>
      )}

      {room.financial_snapshot?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Financial</p>
          <ul className="space-y-1">
            {room.financial_snapshot.map((f, i) => (
              <li key={i} className="text-xs text-gray-700 leading-snug line-clamp-2">• {f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function CompareModal({ rooms, onClose }) {
  const [idA, setIdA] = useState('');
  const [idB, setIdB] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCompare = async () => {
    if (!idA || !idB) return;
    setError('');
    setLoading(true);
    try {
      const data = await compare(idA, idB);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Comparison failed.');
    } finally {
      setLoading(false);
    }
  };

  const [a, b] = result?.deal_rooms ?? [];

  const selectClass = "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 shrink-0">
          <h2 className="font-semibold text-gray-900">Compare Deal Rooms</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        <div className="px-6 py-5 space-y-5 overflow-y-auto">
          {error && (
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg px-4 py-3 text-sm">{error}</div>
          )}

          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Deal Room A</label>
              <select
                value={idA}
                onChange={(e) => { setIdA(e.target.value); setResult(null); }}
                className={selectClass}
              >
                <option value="">Select deal room…</option>
                {rooms.filter((r) => r.id !== idB).map((r) => (
                  <option key={r.id} value={r.id}>{r.target_company}</option>
                ))}
              </select>
            </div>
            <div className="text-gray-400 font-bold pb-2 shrink-0">vs</div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Deal Room B</label>
              <select
                value={idB}
                onChange={(e) => { setIdB(e.target.value); setResult(null); }}
                className={selectClass}
              >
                <option value="">Select deal room…</option>
                {rooms.filter((r) => r.id !== idA).map((r) => (
                  <option key={r.id} value={r.id}>{r.target_company}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleCompare}
              disabled={!idA || !idB || loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? 'Comparing…' : 'Compare'}
            </button>
          </div>

          {result && a && b && (
            <>
              <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-sm text-blue-900 leading-relaxed">
                {buildSummary(a, b)}
              </div>

              <div className="flex gap-4 items-start">
                <SideCard room={a} />
                <div className="flex items-center text-gray-400 font-bold pt-6 shrink-0">vs</div>
                <SideCard room={b} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
