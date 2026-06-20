import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import useDealRoom from '../hooks/useDealRoom';
import useAuthStore from '../store/authStore';
import Topbar from '../components/layout/Topbar';
import DocumentUploader from '../components/documents/DocumentUploader';
import DocumentList from '../components/documents/DocumentList';
import MemberList from '../components/members/MemberList';
import InviteMemberModal from '../components/members/InviteMemberModal';
import * as dealRoomsApiStatic from '../api/dealRooms';
import * as documentsApi from '../api/documents';
import * as reportsApi from '../api/reports';

function Skeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-6 bg-gray-200 rounded w-1/3" />
      <div className="h-4 bg-gray-200 rounded w-1/2" />
      <div className="h-32 bg-gray-200 rounded" />
    </div>
  );
}

export default function DealRoom() {
  const { roomId } = useParams();
  const { user } = useAuthStore();
  const { dealRoom, documents, members, loading, refetch } = useDealRoom(roomId);
  const [showInvite, setShowInvite] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const myMember = members.find((m) => m.user_id === user?.id);
  const myRoomRole = myMember?.role;
  const isRoomOwner = myRoomRole === 'owner';
  const canRunAnalysis = myRoomRole === 'owner' || myRoomRole === 'senior_analyst';

  const handleUploaded = () => refetch();

  const handleDelete = async (docId) => {
    try {
      await documentsApi.remove(roomId, docId);
      refetch();
    } catch {}
  };

  const handleRemoveMember = async (userId) => {
    try {
      await dealRoomsApiStatic.removeMember(roomId, userId);
      refetch();
    } catch {}
  };

  const handleRoleChange = async (userId, role) => {
    try {
      await dealRoomsApiStatic.updateMember(roomId, userId, { role });
      refetch();
    } catch (err) {
      const d = err.response?.data?.detail;
      alert(typeof d === 'string' ? d : 'Failed to update role.');
    }
  };

  const handleTriggerAnalysis = async () => {
    setTriggering(true);
    try {
      const report = await reportsApi.trigger(roomId);
      window.location.href = `/deal-rooms/${roomId}/reports/${report.id}`;
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Failed to start analysis.');
      setTriggering(false);
    }
  };

  const hasIndexed = documents.some((d) => d.status === 'indexed');

  if (loading) {
    return (
      <>
        <Topbar breadcrumbs={[{ to: '/', label: 'Dashboard' }, { label: '…' }]} />
        <main className="flex-1 px-6 py-6"><Skeleton /></main>
      </>
    );
  }

  return (
    <>
      <Topbar
        breadcrumbs={[
          { to: '/', label: 'Dashboard' },
          { label: dealRoom?.target_company ?? 'Deal Room' },
        ]}
      />

      <main className="flex-1 px-6 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{dealRoom?.target_company}</h1>
            {dealRoom?.description && (
              <p className="mt-1 text-sm text-gray-500">{dealRoom.description}</p>
            )}
          </div>
          {canRunAnalysis && (
            <button
              onClick={handleTriggerAnalysis}
              disabled={triggering || !hasIndexed}
              title={!hasIndexed ? 'Upload and index at least one document first' : ''}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {triggering ? 'Starting…' : 'Run Analysis'}
            </button>
          )}
        </div>

        {/* Missing context panel */}
        {dealRoom?.missing_context?.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-amber-800 mb-2">Missing Context</h3>
            <ul className="space-y-1">
              {dealRoom.missing_context.map((item, i) => (
                <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                  <span className="mt-0.5">⚠</span> {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Documents panel */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="font-semibold text-gray-900 mb-4">Documents</h2>
              <DocumentUploader dealRoomId={roomId} onUploaded={handleUploaded} />
              <div className="mt-5">
                <DocumentList documents={documents} dealRoomId={roomId} onDelete={handleDelete} />
              </div>
            </div>

            {/* Reports list */}
            <ReportsList roomId={roomId} />
          </div>

          {/* Members panel */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Members</h2>
              {isRoomOwner && (
                <button
                  onClick={() => setShowInvite(true)}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                >
                  + Invite
                </button>
              )}
            </div>
            <MemberList
  members={members}
  onRemove={isRoomOwner ? handleRemoveMember : null}
  onRoleChange={isRoomOwner ? handleRoleChange : null}
  currentUserId={user?.id}
/>
          </div>
        </div>
      </main>

      {showInvite && (
        <InviteMemberModal
          dealRoomId={roomId}
          onClose={() => setShowInvite(false)}
          onInvited={() => { setShowInvite(false); refetch(); }}
        />
      )}
    </>
  );
}

const PAGE_SIZE = 5;

function ReportsList({ roomId }) {
  const [reports, setReports] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [cancelling, setCancelling] = useState(null);

  const load = (p) =>
    reportsApi
      .list(roomId, { page: p, page_size: PAGE_SIZE })
      .then((d) => { setReports(d.items ?? []); setTotal(d.total ?? 0); })
      .catch(() => { setReports([]); setTotal(0); });

  useEffect(() => { load(1); setPage(1); }, [roomId]);

  const handleCancel = async (e, reportId) => {
    e.preventDefault();
    if (!window.confirm('Cancel this report? This cannot be undone.')) return;
    setCancelling(reportId);
    try {
      await reportsApi.cancel(roomId, reportId);
      await load(page);
    } catch {
      alert('Failed to cancel report.');
    } finally {
      setCancelling(null);
    }
  };

  const handlePage = (next) => { setPage(next); load(next); };

  if (!reports) return null;
  if (reports.length === 0 && page === 1) return null;

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const STATUS_COLORS = {
    pending: 'text-yellow-600',
    running: 'text-blue-600',
    draft: 'text-gray-500',
    failed: 'text-red-500',
    in_review: 'text-purple-600',
    approved: 'text-green-600',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-gray-900">Analysis Reports</h2>
        <span className="text-xs text-gray-400">{total} total</span>
      </div>
      <div className="space-y-2">
        {reports.map((r) => (
          <div key={r.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
            <Link
              to={`/deal-rooms/${roomId}/reports/${r.id}`}
              className="flex-1 hover:text-blue-600 transition-colors"
            >
              <p className="text-sm font-medium text-gray-800">{new Date(r.created_at).toLocaleString()}</p>
              <p className={`text-xs capitalize ${STATUS_COLORS[r.status] ?? 'text-gray-400'}`}>{r.status}</p>
            </Link>
            {(r.status === 'pending' || r.status === 'running') && (
              <button
                onClick={(e) => handleCancel(e, r.id)}
                disabled={cancelling === r.id}
                className="ml-3 text-xs px-2 py-1 text-red-600 border border-red-200 rounded hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                {cancelling === r.id ? '…' : 'Cancel'}
              </button>
            )}
          </div>
        ))}
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
          <button
            onClick={() => handlePage(page - 1)}
            disabled={page === 1}
            className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
          <button
            onClick={() => handlePage(page + 1)}
            disabled={page === totalPages}
            className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
