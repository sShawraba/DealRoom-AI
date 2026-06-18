import { useState } from 'react';
import { resolve, reply } from '../../api/annotations';

const TYPE_STYLES = {
  comment:  'bg-gray-100 text-gray-600',
  verified: 'bg-green-100 text-green-700',
  disputed: 'bg-red-100 text-red-700',
};

function AnnotationItem({ annotation, onResolved }) {
  const [replyText, setReplyText] = useState('');
  const [showReply, setShowReply] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleReply = async (e) => {
    e.preventDefault();
    if (!replyText.trim()) return;
    setLoading(true);
    try {
      await reply(annotation.id, { content: replyText });
      setReplyText('');
      setShowReply(false);
    } catch {}
    finally { setLoading(false); }
  };

  const handleResolve = async () => {
    setLoading(true);
    try {
      await resolve(annotation.id);
      onResolved?.();
    } catch {}
    finally { setLoading(false); }
  };

  return (
    <div className={`rounded-lg border p-3 ${annotation.resolved ? 'opacity-60 border-gray-100' : 'border-gray-200'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-gray-700">{annotation.author_email ?? annotation.author_name ?? 'User'}</span>
          <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full capitalize ${TYPE_STYLES[annotation.type] ?? TYPE_STYLES.comment}`}>
            {annotation.type}
          </span>
          {annotation.resolved && <span className="text-xs text-gray-400 italic">resolved</span>}
        </div>
        <span className="text-xs text-gray-400 shrink-0">
          {annotation.created_at ? new Date(annotation.created_at).toLocaleDateString() : ''}
        </span>
      </div>

      <p className="mt-2 text-sm text-gray-700">{annotation.content}</p>

      {annotation.replies?.map((r) => (
        <div key={r.id} className="mt-2 ml-4 pl-3 border-l-2 border-gray-200">
          <p className="text-xs text-gray-500 mb-0.5">{r.author_email ?? 'User'}</p>
          <p className="text-sm text-gray-700">{r.content}</p>
        </div>
      ))}

      {!annotation.resolved && (
        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={() => setShowReply((v) => !v)}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            Reply
          </button>
          {annotation.type === 'disputed' && (
            <button
              onClick={handleResolve}
              disabled={loading}
              className="text-xs text-green-600 hover:text-green-800"
            >
              Resolve
            </button>
          )}
        </div>
      )}

      {showReply && (
        <form onSubmit={handleReply} className="mt-2 flex gap-2">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Write a reply…"
            className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg disabled:opacity-60"
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}

export default function AnnotationThread({ annotations = [], onResolved }) {
  if (annotations.length === 0) {
    return <p className="text-sm text-gray-400 py-2">No annotations.</p>;
  }

  return (
    <div className="space-y-3">
      {annotations.map((a) => (
        <AnnotationItem key={a.id} annotation={a} onResolved={onResolved} />
      ))}
    </div>
  );
}
