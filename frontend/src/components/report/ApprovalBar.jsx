import { useState } from 'react';
import { changeStatus } from '../../api/reports';

const errMsg = (err, fallback) => {
  const d = err.response?.data?.detail;
  if (!d) return fallback;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e) => e.msg ?? JSON.stringify(e)).join(', ');
  return fallback;
};

const STATUS_LABEL = {
  draft:     { text: 'Draft',       cls: 'bg-gray-100 text-gray-600' },
  in_review: { text: 'In Review',   cls: 'bg-blue-100 text-blue-700' },
  approved:  { text: 'Approved',    cls: 'bg-green-100 text-green-700' },
};

export default function ApprovalBar({ report, dealRoomId, userRole, disputedCount, onStatusChange, onExportPDF, onExportWord }) {
  const [loading, setLoading] = useState(false);

  if (!report) return null;

  const isApproved = report.status === 'approved';
  const canApprove = userRole === 'owner' || userRole === 'senior_analyst';
  const statusMeta = STATUS_LABEL[report.status] ?? STATUS_LABEL.draft;

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await changeStatus(dealRoomId, report.id, { action: 'submit_for_review' });
      onStatusChange?.();
    } catch (err) {
      alert(errMsg(err, 'Failed to submit.'));
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (disputedCount > 0) return;
    setLoading(true);
    try {
      await changeStatus(dealRoomId, report.id, { action: 'approve' });
      onStatusChange?.();
    } catch (err) {
      alert(errMsg(err, 'Failed to approve.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="shrink-0 border-t border-gray-200 bg-white shadow-[0_-2px_8px_rgba(0,0,0,0.04)] px-6 py-3 flex items-center justify-between gap-4">
      {/* Left: status + warnings */}
      <div className="flex items-center gap-3 min-w-0">
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full whitespace-nowrap ${statusMeta.cls}`}>
          {statusMeta.text}
        </span>

        {isApproved && report.approved_by_name && (
          <span className="text-xs text-gray-500 truncate">
            Approved by {report.approved_by_name}
            {report.approved_at && ` · ${new Date(report.approved_at).toLocaleDateString()}`}
          </span>
        )}

        {!isApproved && disputedCount > 0 && (
          <span className="text-xs text-red-600">
            ⚠ {disputedCount} disputed annotation{disputedCount !== 1 ? 's' : ''} — resolve before approving
          </span>
        )}
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-2 shrink-0">
        {isApproved && (
          <>
            <button
              onClick={onExportWord}
              className="px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              ↓ Word
            </button>
            <button
              onClick={onExportPDF}
              className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-900 text-white rounded-lg transition-colors"
            >
              ↓ PDF
            </button>
          </>
        )}

        {report.status === 'draft' && (
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? 'Submitting…' : 'Submit for review'}
          </button>
        )}

        {report.status === 'in_review' && canApprove && (
          <div title={disputedCount > 0 ? `Resolve ${disputedCount} disputed annotation${disputedCount !== 1 ? 's' : ''} first` : ''}>
            <button
              onClick={handleApprove}
              disabled={loading || disputedCount > 0}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? 'Approving…' : '✓ Approve report'}
            </button>
          </div>
        )}

        {report.status === 'in_review' && !canApprove && (
          <span className="text-xs text-gray-400 italic">Awaiting manager approval</span>
        )}
      </div>
    </div>
  );
}
