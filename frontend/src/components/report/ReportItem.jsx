import { useState } from 'react';
import { updateItem } from '../../api/reports';
import * as annotationsApi from '../../api/annotations';
import AnnotationThread from '../annotations/AnnotationThread';

const ANNOTATION_TYPES = ['comment', 'verified', 'disputed'];
const TYPE_CONFIG = {
  comment:  { label: '💬 Comment',  cls: 'bg-blue-100 border-blue-300 text-blue-700' },
  verified: { label: '✓ Verified',  cls: 'bg-green-100 border-green-300 text-green-700' },
  disputed: { label: '⚠ Disputed',  cls: 'bg-red-100 border-red-300 text-red-700' },
};

export default function ReportItem({
  item, dealRoomId, reportId, annotations = [],
  isApproved, onCitationClick, onRefreshAnnotations, onItemSaved,
}) {
  const [editing, setEditing]         = useState(false);
  const [editValue, setEditValue]     = useState('');
  const [saving, setSaving]           = useState(false);
  const [showPanel, setShowPanel]     = useState(false);
  const [noteType, setNoteType]       = useState('comment');
  const [noteContent, setNoteContent] = useState('');
  const [posting, setPosting]         = useState(false);

  const raw = item.edited_content ?? item.content ?? '';
  // Extract inline [SOURCE: file.pdf, p.N] as fallback when the structured citation field is absent
  const SOURCE_RE = /\[SOURCE:\s*([^\],\]]+?)(?:,\s*p\.?\s*(\d+))?\]/i;
  const sourceMatch = !item.citation ? SOURCE_RE.exec(raw) : null;
  const citation = item.citation || (sourceMatch ? {
    source_name: sourceMatch[1].trim(),
    page_number: sourceMatch[2] ? parseInt(sourceMatch[2], 10) : null,
  } : null);
  const content = raw.replace(/\s*\[SOURCE:[^\]]*\]/gi, '').trim();
  const unresolvedDisputed = annotations.filter((a) => a.type === 'disputed' && !a.resolved).length;
  const hasAnnotations = annotations.length > 0;

  const handleEdit = () => { setEditValue(content); setEditing(true); };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateItem(dealRoomId, reportId, item.id, { edited_content: editValue });
      setEditing(false);
      await onItemSaved?.();
    } catch (err) {
      const d = err.response?.data?.detail;
      const msg = typeof d === 'string' ? d : Array.isArray(d) ? d.map((e) => e.msg ?? JSON.stringify(e)).join(', ') : 'Failed to save.';
      alert(msg);
    } finally {
      setSaving(false);
    }
  };

  const handlePost = async (e) => {
    e.preventDefault();
    if (!noteContent.trim()) return;
    setPosting(true);
    try {
      await annotationsApi.create(dealRoomId, {
        report_item_id: item.id,
        content: noteContent,
        type: noteType,
      });
      setNoteContent('');
      setShowPanel(true);
      await onRefreshAnnotations?.();
    } catch {}
    finally { setPosting(false); }
  };

  return (
    <div className="group relative mb-4 last:mb-0">
      {/* Unverified left-border indicator */}
      {!item.is_verified && (
        <div className="absolute left-0 top-0 bottom-0 w-0.5 rounded-full bg-amber-400" />
      )}

      {editing ? (
        /* ── Edit mode ─────────────────────────────────── */
        <div className={`space-y-2 ${!item.is_verified ? 'pl-3' : ''}`}>
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            rows={4}
            autoFocus
            className="w-full text-sm border border-blue-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs rounded-lg transition-colors"
            >
              {saving ? 'Saving…' : 'Save changes'}
            </button>
            <button
              onClick={() => setEditing(false)}
              className="px-3 py-1.5 text-xs text-gray-500 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        /* ── Read mode ─────────────────────────────────── */
        <div className={`pr-20 ${!item.is_verified ? 'pl-3' : ''}`}>
          <span className="text-sm text-gray-800 leading-relaxed">
            {content}
          </span>

          {/* Inline markers */}
          {item.edited_content && (
            <span className="ml-1.5 text-xs text-blue-500 italic">
              (edited{item.edited_by_email ? ` by ${item.edited_by_email}` : ''})
            </span>
          )}
          {citation && (
            <button
              onClick={() => onCitationClick?.(citation)}
              className="ml-1 text-xs text-blue-500 hover:text-blue-700 font-medium align-super"
              title={`Source: ${citation.source_name ?? citation.filename ?? 'document'}${citation.page_number ?? citation.page ? `, p.${citation.page_number ?? citation.page}` : ''}`}
            >
              [src]
            </button>
          )}
        </div>
      )}

      {/* Right-margin action buttons ─────────────────── */}
      {!editing && (
        <div className="absolute right-0 top-0 flex items-center gap-1">
          {/* Comment/annotation toggle — always visible if has annotations */}
          <button
            onClick={() => setShowPanel((v) => !v)}
            title={showPanel ? 'Hide comments' : 'Comments'}
            className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-lg border bg-white transition-all ${
              hasAnnotations || showPanel ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
            } ${
              showPanel
                ? 'border-blue-200 text-blue-700 bg-blue-50'
                : unresolvedDisputed > 0
                ? 'border-red-200 text-red-600'
                : hasAnnotations
                ? 'border-gray-200 text-gray-500'
                : 'border-gray-200 text-gray-400'
            }`}
          >
            <span>{unresolvedDisputed > 0 ? '⚠' : '💬'}</span>
            {hasAnnotations && <span>{annotations.length}</span>}
          </button>

          {/* Edit — hover only */}
          {!isApproved && (
            <button
              onClick={handleEdit}
              title="Edit"
              className="opacity-0 group-hover:opacity-100 text-xs text-gray-400 border border-gray-200 bg-white px-2 py-1 rounded-lg hover:text-gray-700 hover:bg-gray-50 transition-all"
            >
              ✏
            </button>
          )}
        </div>
      )}

      {/* Inline annotation panel ──────────────────────── */}
      {showPanel && (
        <div className="mt-3 pl-4 border-l-2 border-blue-200 space-y-3 bg-blue-50/40 rounded-r-lg py-3 pr-3">
          {annotations.length > 0 && (
            <AnnotationThread annotations={annotations} onResolved={onRefreshAnnotations} />
          )}

          {!isApproved && (
            <form onSubmit={handlePost} className="space-y-2 pt-1">
              <div className="flex gap-2 flex-wrap">
                {ANNOTATION_TYPES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setNoteType(t)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                      noteType === t ? TYPE_CONFIG[t].cls : 'border-gray-200 text-gray-500 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {TYPE_CONFIG[t].label}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={noteContent}
                  onChange={(e) => setNoteContent(e.target.value)}
                  placeholder={
                    noteType === 'disputed' ? 'Explain what you dispute…'
                    : noteType === 'verified' ? 'Add verification note…'
                    : 'Add a comment…'
                  }
                  className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  disabled={posting || !noteContent.trim()}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs rounded-lg whitespace-nowrap transition-colors"
                >
                  {posting ? '…' : 'Post'}
                </button>
              </div>
            </form>
          )}

          {annotations.length === 0 && isApproved && (
            <p className="text-xs text-gray-400 italic">No annotations on this finding.</p>
          )}
        </div>
      )}
    </div>
  );
}
