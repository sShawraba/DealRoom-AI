import { useState } from 'react';

const ROLE_STYLES = {
  owner:          'bg-purple-100 text-purple-700',
  senior_analyst: 'bg-blue-100 text-blue-700',
  analyst:        'bg-gray-100 text-gray-600',
  viewer:         'bg-gray-100 text-gray-400',
};

const ROLE_LABELS = {
  owner:          'Owner',
  senior_analyst: 'Senior Analyst',
  analyst:        'Analyst',
  viewer:         'Viewer',
};

const ROLE_OPTIONS = ['owner', 'senior_analyst', 'analyst', 'viewer'];

export default function MemberList({ members, onRemove, onRoleChange, currentUserId }) {
  const [changingId, setChangingId] = useState(null);
  const [pendingRole, setPendingRole] = useState('');
  const [saving, setSaving] = useState(false);

  const startChange = (member) => {
    setChangingId(member.user_id);
    setPendingRole(member.role);
  };

  const cancelChange = () => {
    setChangingId(null);
    setPendingRole('');
  };

  const confirmChange = async (userId) => {
    setSaving(true);
    try {
      await onRoleChange?.(userId, pendingRole);
      setChangingId(null);
    } finally {
      setSaving(false);
    }
  };

  if (!members || members.length === 0) {
    return <p className="text-sm text-gray-400 py-4">No members.</p>;
  }

  return (
    <div className="space-y-1">
      {members.map((m) => {
        const isChanging = changingId === m.user_id;
        const isSelf = m.user_id === currentUserId;

        return (
          <div
            key={m.user_id}
            className="flex items-center justify-between py-2.5 border-b border-gray-100 last:border-0 gap-3"
          >
            {/* Identity */}
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{m.full_name ?? m.email}</p>
              {m.full_name && <p className="text-xs text-gray-400 truncate">{m.email}</p>}
            </div>

            {/* Role + actions */}
            <div className="flex items-center gap-2 shrink-0">
              {isChanging ? (
                /* Inline role selector */
                <>
                  <select
                    value={pendingRole}
                    onChange={(e) => setPendingRole(e.target.value)}
                    autoFocus
                    className="border border-gray-300 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {ROLE_OPTIONS.map((r) => (
                      <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => confirmChange(m.user_id)}
                    disabled={saving || pendingRole === m.role}
                    className="text-xs px-2.5 py-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg transition-colors"
                  >
                    {saving ? '…' : 'Save'}
                  </button>
                  <button
                    onClick={cancelChange}
                    className="text-xs text-gray-400 hover:text-gray-600"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                /* Normal view */
                <>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ROLE_STYLES[m.role] ?? ROLE_STYLES.viewer}`}>
                    {ROLE_LABELS[m.role] ?? m.role}
                  </span>
                  {!isSelf && onRoleChange && (
                    <button
                      onClick={() => startChange(m)}
                      className="text-xs text-gray-400 hover:text-blue-600 transition-colors"
                      title="Change role"
                    >
                      Change role
                    </button>
                  )}
                  {!isSelf && onRemove && (
                    <button
                      onClick={() => onRemove(m.user_id)}
                      className="text-xs text-red-400 hover:text-red-600 transition-colors"
                    >
                      Remove
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
