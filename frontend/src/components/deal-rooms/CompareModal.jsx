import { useState } from 'react';
import { compare } from '../../api/dealRooms';
import { RISK_COLORS } from './DealRoomCard';

export default function CompareModal({ rooms, onClose }) {
  const [selectedId, setSelectedId] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const baseRoom = rooms[0];

  const handleCompare = async () => {
    if (!selectedId) return;
    setError('');
    setLoading(true);
    try {
      const data = await compare(baseRoom.id, selectedId);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Comparison failed.');
    } finally {
      setLoading(false);
    }
  };

  const renderSide = (room) => {
    const tier = room.risk_tier ?? 'null';
    const colors = RISK_COLORS[tier] ?? RISK_COLORS.null;
    return (
      <div className={`flex-1 rounded-xl border-2 ${colors.border} ${colors.bg} p-5`}>
        <h3 className="font-semibold text-gray-900">{room.company_name}</h3>
        {room.risk_score != null && (
          <p className={`text-3xl font-bold mt-2 ${colors.text}`}>{room.risk_score}</p>
        )}
        <p className={`text-sm mt-1 capitalize font-medium ${colors.text}`}>{tier} risk</p>
        {room.red_flag_count != null && (
          <p className="text-xs text-gray-500 mt-2">{room.red_flag_count} red flags</p>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">Compare Deal Rooms</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {error && (
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg px-4 py-3 text-sm">{error}</div>
          )}

          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Base: {baseRoom?.company_name}</label>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Compare with</label>
              <select
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select deal room…</option>
                {rooms.slice(1).map((r) => (
                  <option key={r.id} value={r.id}>{r.company_name}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleCompare}
              disabled={!selectedId || loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? 'Comparing…' : 'Compare'}
            </button>
          </div>

          {result && (
            <div className="flex gap-4 mt-4">
              {renderSide(result.room_1)}
              <div className="flex items-center text-gray-400 font-bold">vs</div>
              {renderSide(result.room_2)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
