import { useState } from 'react';

const ACTION_COLORS = {
  'user.registered':              'bg-blue-100 text-blue-700',
  'user.login':                   'bg-brand-warm text-brand-taupe',
  'user.login_failed':            'bg-red-100 text-red-700',
  'deal_room.created':            'bg-green-100 text-green-700',
  'deal_room.updated':            'bg-yellow-100 text-yellow-700',
  'deal_room.deleted':            'bg-red-100 text-red-700',
  'deal_room.accessed':           'bg-gray-100 text-gray-600',
  'document.uploaded':            'bg-purple-100 text-purple-700',
  'document.downloaded':          'bg-indigo-100 text-indigo-700',
  'document.deleted':             'bg-red-100 text-red-700',
  'report.submitted_for_review':  'bg-orange-100 text-orange-700',
  'report.approved':              'bg-green-100 text-green-700',
  'annotation.created':           'bg-blue-100 text-blue-700',
  'annotation.disputed':          'bg-red-100 text-red-700',
  'annotation.resolved':          'bg-green-100 text-green-700',
  'permission.member_invited':    'bg-indigo-100 text-indigo-700',
  'permission.document_restricted': 'bg-amber-100 text-amber-700',
  'analysis.started':             'bg-cyan-100 text-cyan-700',
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

  const inputCls = 'border border-brand-sand rounded-lg px-3 py-1.5 text-sm bg-white text-brand-ink placeholder-brand-taupe focus:outline-none focus:border-brand-green focus:ring-1 focus:ring-brand-green';

  return (
    <div className="space-y-4">
      {/* Filters — always visible so clicking them is responsive */}
      <div className="bg-white rounded-xl border border-brand-sand p-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Filter by user email…"
            value={active.user}
            onChange={(e) => setActive((f) => ({ ...f, user: e.target.value }))}
            className={`${inputCls} flex-1 min-w-48`}
          />
          <input
            type="date"
            value={active.dateFrom}
            onChange={(e) => setActive((f) => ({ ...f, dateFrom: e.target.value }))}
            className={inputCls}
          />
          <input
            type="date"
            value={active.dateTo}
            onChange={(e) => setActive((f) => ({ ...f, dateTo: e.target.value }))}
            className={inputCls}
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {FILTER_ACTIONS.map((action) => (
            <button
              key={action}
              onClick={() => toggleAction(action)}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                active.actions.includes(action)
                  ? 'border-brand-green bg-brand-green text-brand-cream'
                  : 'border-brand-sand text-brand-taupe hover:border-brand-taupe'
              }`}
            >
              {action.replace(/[._]/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Event list */}
      {loading ? (
        <div className="space-y-3 animate-pulse">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-brand-sand rounded-lg" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-12 text-brand-taupe">
          <p className="text-2xl mb-2">◈</p>
          <p className="text-sm">No events found.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-brand-sand divide-y divide-brand-sand">
          {events.map((event) => {
            const actionStyle = ACTION_COLORS[event.action] ?? 'bg-brand-warm text-brand-taupe';
            return (
              <div key={event.id} className="px-5 py-3 flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${actionStyle}`}>
                      {event.action?.replace(/[._]/g, ' ')}
                    </span>
                    <span className="text-xs text-brand-taupe truncate">{event.actor_email}</span>
                    {event.resource_name && (
                      <span className="text-xs text-brand-sand truncate">· {event.resource_name}</span>
                    )}
                  </div>
                  {event.ip_address && (
                    <p className="text-xs text-brand-taupe mt-0.5">{event.ip_address}</p>
                  )}
                </div>
                <span className="text-xs text-brand-taupe shrink-0">
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
