import { useState } from 'react';

const ACTION_COLORS = {
  USER_REGISTERED:           'bg-blue-100 text-blue-700',
  USER_LOGGED_IN:            'bg-gray-100 text-gray-600',
  DEAL_ROOM_CREATED:         'bg-green-100 text-green-700',
  DEAL_ROOM_UPDATED:         'bg-yellow-100 text-yellow-700',
  DOCUMENT_UPLOADED:         'bg-purple-100 text-purple-700',
  REPORT_TRIGGERED:          'bg-orange-100 text-orange-700',
  REPORT_APPROVED:           'bg-green-100 text-green-700',
  ANNOTATION_CREATED:        'bg-blue-100 text-blue-700',
  ANNOTATION_DISPUTED:       'bg-red-100 text-red-700',
  ANNOTATION_RESOLVED:       'bg-green-100 text-green-700',
  MEMBER_ADDED:              'bg-indigo-100 text-indigo-700',
  PERMISSION_DOC_RESTRICTED: 'bg-amber-100 text-amber-700',
};

const FILTER_ACTIONS = Object.keys(ACTION_COLORS);

export default function ActivityFeed({ events = [], loading, onFilterChange, filters }) {
  const [localFilters, setLocalFilters] = useState({ user: '', actions: [], dateFrom: '', dateTo: '' });

  const active = filters ?? localFilters;
  const setActive = onFilterChange ?? setLocalFilters;

  const toggleAction = (action) => {
    setActive((f) => ({
      ...f,
      actions: f.actions.includes(action)
        ? f.actions.filter((a) => a !== action)
        : [...f.actions, action],
    }));
  };

  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-12 bg-gray-200 rounded-lg" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Filter by user email…"
            value={active.user}
            onChange={(e) => setActive((f) => ({ ...f, user: e.target.value }))}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 flex-1 min-w-48"
          />
          <input
            type="date"
            value={active.dateFrom}
            onChange={(e) => setActive((f) => ({ ...f, dateFrom: e.target.value }))}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="date"
            value={active.dateTo}
            onChange={(e) => setActive((f) => ({ ...f, dateTo: e.target.value }))}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {FILTER_ACTIONS.map((action) => (
            <button
              key={action}
              onClick={() => toggleAction(action)}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                active.actions.includes(action)
                  ? 'border-blue-400 bg-blue-50 text-blue-700'
                  : 'border-gray-200 text-gray-500 hover:border-gray-400'
              }`}
            >
              {action.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Event list */}
      {events.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-2xl mb-2">📋</p>
          <p className="text-sm">No events found.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {events.map((event) => {
            const actionStyle = ACTION_COLORS[event.action] ?? 'bg-gray-100 text-gray-600';
            return (
              <div key={event.id} className="px-5 py-3 flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${actionStyle}`}>
                      {event.action?.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs text-gray-500 truncate">{event.actor_email}</span>
                    {event.resource_name && (
                      <span className="text-xs text-gray-400 truncate">· {event.resource_name}</span>
                    )}
                  </div>
                  {event.ip_address && (
                    <p className="text-xs text-gray-400 mt-0.5">{event.ip_address}</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 shrink-0">
                  {event.occurred_at ? new Date(event.occurred_at).toLocaleString() : ''}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
