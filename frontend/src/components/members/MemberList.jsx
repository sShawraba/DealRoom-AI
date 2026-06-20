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

export default function MemberList({ members, onRemove, currentUserId }) {
  if (!members || members.length === 0) {
    return <p className="text-sm text-gray-400 py-4">No members.</p>;
  }

  return (
    <div className="space-y-2">
      {members.map((m) => (
        <div key={m.user_id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
          <div>
            <p className="text-sm font-medium text-gray-900">{m.full_name ?? m.email}</p>
            <p className="text-xs text-gray-400">{m.email}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ROLE_STYLES[m.role] ?? ROLE_STYLES.viewer}`}>
              {ROLE_LABELS[m.role] ?? m.role}
            </span>
            {m.user_id !== currentUserId && onRemove && (
              <button onClick={() => onRemove(m.user_id)} className="text-xs text-red-500 hover:text-red-700">
                Remove
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
