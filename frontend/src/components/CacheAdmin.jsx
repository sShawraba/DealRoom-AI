import { useState } from 'react';
import client from '../api/client';

function CacheButton({ label, onClick, loading, success, error }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-700">{label}</span>
      <div className="flex items-center gap-2">
        {success && <span className="text-xs text-green-600">Cleared</span>}
        {error && <span className="text-xs text-red-600">{error}</span>}
        <button
          onClick={onClick}
          disabled={loading}
          className="px-3 py-1.5 text-xs bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-lg disabled:opacity-60 transition-colors"
        >
          {loading ? 'Clearing…' : 'Clear'}
        </button>
      </div>
    </div>
  );
}

export default function CacheAdmin({ dealRoomId, companyName }) {
  const [states, setStates] = useState({ embedding: {}, research: {}, ml: {} });

  const set = (key, patch) => setStates((s) => ({ ...s, [key]: { ...s[key], ...patch } }));

  const clearEmbedding = async () => {
    set('embedding', { loading: true, success: false, error: null });
    try {
      await client.post('/admin/cache/clear');
      set('embedding', { loading: false, success: true });
    } catch (err) {
      set('embedding', { loading: false, error: err.response?.data?.detail ?? 'Failed' });
    }
  };

  const clearResearch = async () => {
    if (!companyName) return;
    set('research', { loading: true, success: false, error: null });
    try {
      await client.delete(`/admin/cache/research/${encodeURIComponent(companyName)}`);
      set('research', { loading: false, success: true });
    } catch (err) {
      set('research', { loading: false, error: err.response?.data?.detail ?? 'Failed' });
    }
  };

  const clearML = async () => {
    set('ml', { loading: true, success: false, error: null });
    try {
      await client.delete('/admin/cache/ml');
      set('ml', { loading: false, success: true });
    } catch (err) {
      set('ml', { loading: false, error: err.response?.data?.detail ?? 'Failed' });
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-900 text-sm mb-3">Cache Management</h3>
      <CacheButton
        label="Clear embedding cache for this deal room"
        onClick={clearEmbedding}
        {...states.embedding}
      />
      <CacheButton
        label={`Clear research cache for ${companyName ?? 'company'}`}
        onClick={clearResearch}
        {...states.research}
      />
      <CacheButton
        label="Clear ML risk score cache"
        onClick={clearML}
        {...states.ml}
      />
    </div>
  );
}
