import { useState } from 'react';
import { resolve, reply } from '../../api/annotations';

const TYPE_STYLES = {
  comment:  'bg-gray-100 text-gray-600',
  verified: 'bg-green-100 text-green-700',
  disputed: 'bg-red-100 text-red-700',
};

const displayName = (obj) =>
  obj?.author_name || obj?.author_email || 'Unknown user';

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
      onResolved?.();  // triggers fetchAnnotations in parent to reload with new reply
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
    <div className={`rounded-lg border p-3 ${annotation.resolved ? 'opacity-60 border-gray-100' : 'border-gray-200 bg-white'}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-gray-800">{displayName(annotation)}</span>
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

      {/* Replies */}
      {annotation.replies?.length > 0 && (
        <div className="mt-2 space-y-2">
          {annotation.replies.map((r) => (
            <div key={r.id} className="ml-4 pl-3 border-l-2 border-gray-200">
              <span className="text-xs font-semibold text-gray-600">{displayName(r)}</span>
              <span className="ml-1.5 text-xs text-gray-400">{new Date(r.created_at).toLocaleDateString()}</span>
              <p className="text-sm text-gray-700 mt-0.5">{r.content}</p>
            </div>
          ))}
        </div>
      )}

      {!annotation.resolved && (
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={() => setShowReply((v) => !v)}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            {showReply ? 'Cancel' : 'Reply'}
          </button>
          {annotation.type === 'disputed' && (
            <button
              onClick={handleResolve}
              disabled={loading}
              className="text-xs text-green-700 hover:text-green-900 font-medium"
            >
              {loading ? '…' : 'Mark resolved'}
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
            autoFocus
            className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading || !replyText.trim()}
            className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg disabled:opacity-60"
          >
            {loading ? '…' : 'Send'}
          </button>
        </form>
      )}
    </div>
  );
}

export default function AnnotationThread({ annotations = [], onResolved }) {
  if (annotations.length === 0) {
    return <p className="text-sm text-gray-400 py-1">No annotations yet.</p>;
  }

  return (
    <div className="space-y-2">
      {annotations.map((a) => (
        <AnnotationItem key={a.id} annotation={a} onResolved={onResolved} />
      ))}
    </div>
  );
}
