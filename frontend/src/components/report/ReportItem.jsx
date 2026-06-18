import { useState } from 'react';
import { updateItem } from '../../api/reports';
import AnnotationBadge from '../annotations/AnnotationBadge';

export default function ReportItem({ item, dealRoomId, reportId, annotations = [], isApproved, onCitationClick, onAnnotationClick }) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  const content = item.edited_content ?? item.ai_content ?? '';

  const handleEdit = () => {
    setEditValue(content);
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateItem(dealRoomId, reportId, item.id, { edited_content: editValue });
      setEditing(false);
    } catch {}
    finally { setSaving(false); }
  };

  return (
    <div className="py-3 border-b border-gray-100 last:border-0">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {editing ? (
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              rows={4}
              className="w-full text-sm border border-blue-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          ) : (
            <p className="text-sm text-gray-800 leading-relaxed">
              {content}
              {item.edited_content && (
                <span className="ml-2 text-xs text-blue-500 italic">(edited)</span>
              )}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {annotations.length > 0 && (
            <AnnotationBadge annotations={annotations} onClick={() => onAnnotationClick?.(item.id)} />
          )}
          {item.citations?.length > 0 && (
            <button
              onClick={() => onCitationClick?.(item.citations[0])}
              className="text-xs text-blue-500 hover:text-blue-700"
              title="View source"
            >
              [src]
            </button>
          )}
          {!isApproved && (
            editing ? (
              <div className="flex gap-1">
                <button onClick={handleSave} disabled={saving} className="text-xs text-green-600 hover:text-green-800">
                  {saving ? '…' : 'Save'}
                </button>
                <button onClick={() => setEditing(false)} className="text-xs text-gray-400 hover:text-gray-600">
                  Cancel
                </button>
              </div>
            ) : (
              <button onClick={handleEdit} className="text-xs text-gray-400 hover:text-gray-700" title="Edit">
                ✏
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}
