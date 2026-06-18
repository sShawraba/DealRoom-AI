import { useState } from 'react';
import { changeStatus } from '../../api/reports';

export default function ApprovalBar({ report, dealRoomId, userRole, disputedCount, onStatusChange }) {
  const [loading, setLoading] = useState(false);

  if (!report) return null;

  const isApproved = report.status === 'approved';
  const canApprove = userRole === 'owner' || userRole === 'manager';

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await changeStatus(dealRoomId, report.id, { status: 'submitted' });
      onStatusChange?.();
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Failed to submit.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (disputedCount > 0) return;
    setLoading(true);
    try {
      await changeStatus(dealRoomId, report.id, { status: 'approved' });
      onStatusChange?.();
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Failed to approve.');
    } finally {
      setLoading(false);
    }
  };

  if (isApproved) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-green-600 text-lg">✓</span>
          <div>
            <p className="text-sm font-semibold text-green-800">Report Approved</p>
            {report.approved_by_name && (
              <p className="text-xs text-green-600">
                by {report.approved_by_name}
                {report.approved_at && ` · ${new Date(report.approved_at).toLocaleDateString()}`}
              </p>
            )}
          </div>
        </div>
        <button
          onClick={() => window.print()}
          className="px-4 py-2 text-sm border border-green-400 text-green-700 rounded-lg hover:bg-green-100 transition-colors"
        >
          Export
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl px-5 py-3 flex items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize ${
          report.status === 'submitted' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
        }`}>
          {report.status ?? 'draft'}
        </span>
        {disputedCount > 0 && (
          <span className="text-xs text-red-600">{disputedCount} disputed annotation{disputedCount !== 1 ? 's' : ''} unresolved</span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {report.status === 'draft' && (
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? 'Submitting…' : 'Submit for review'}
          </button>
        )}

        {report.status === 'submitted' && canApprove && (
          <div title={disputedCount > 0 ? `${disputedCount} disputed annotation${disputedCount !== 1 ? 's' : ''} must be resolved` : ''}>
            <button
              onClick={handleApprove}
              disabled={loading || disputedCount > 0}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
            >
              {loading ? 'Approving…' : 'Approve'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
