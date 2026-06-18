import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import * as reportsApi from '../api/reports';
import * as annotationsApi from '../api/annotations';
import * as managementQAApi from '../api/managementQA';
import useAuthStore from '../store/authStore';
import usePolling from '../hooks/usePolling';
import Topbar from '../components/layout/Topbar';
import RiskScoreCard from '../components/report/RiskScoreCard';
import ReportSection from '../components/report/ReportSection';
import ApprovalBar from '../components/report/ApprovalBar';
import CitationPanel from '../components/report/CitationPanel';
import AnnotationThread from '../components/annotations/AnnotationThread';

function Skeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 bg-gray-200 rounded w-1/4" />
      <div className="h-32 bg-gray-200 rounded" />
      <div className="h-48 bg-gray-200 rounded" />
    </div>
  );
}

function QAPanel({ dealRoomId, reportId }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [emailModal, setEmailModal] = useState(false);
  const [emailData, setEmailData] = useState({ to: '', subject: '' });

  useEffect(() => {
    managementQAApi.list(dealRoomId, reportId, { page: 1, page_size: 50 })
      .then((d) => setQuestions(d.items ?? []))
      .catch(() => {});
  }, [dealRoomId, reportId]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await managementQAApi.generate(dealRoomId, reportId);
      const d = await managementQAApi.list(dealRoomId, reportId, { page: 1, page_size: 50 });
      setQuestions(d.items ?? []);
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Failed to generate Q&A.');
    } finally {
      setGenerating(false);
    }
  };

  const handleSendEmail = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await managementQAApi.sendEmail(dealRoomId, reportId, emailData);
      setEmailModal(false);
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Failed to send email.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Management Q&A</h3>
        <div className="flex gap-2">
          {questions.length > 0 && (
            <button
              onClick={() => setEmailModal(true)}
              className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Send email
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white rounded-lg transition-colors"
          >
            {generating ? 'Generating…' : 'Generate Q&A'}
          </button>
        </div>
      </div>

      {questions.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No questions generated yet.</p>
      ) : (
        <div className="space-y-3">
          {questions.map((q) => (
            <div key={q.id} className="bg-white rounded-lg border border-gray-200 p-4">
              <p className="text-sm font-medium text-gray-800">{q.question}</p>
              {q.answer_notes && (
                <p className="mt-2 text-sm text-gray-600 italic">{q.answer_notes}</p>
              )}
              <p className="mt-1 text-xs text-gray-400 capitalize">{q.status ?? 'pending'}</p>
            </div>
          ))}
        </div>
      )}

      {emailModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h4 className="font-semibold text-gray-900">Send Q&A by Email</h4>
              <button onClick={() => setEmailModal(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>
            <form onSubmit={handleSendEmail} className="px-6 py-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">To</label>
                <input
                  type="email"
                  value={emailData.to}
                  onChange={(e) => setEmailData((d) => ({ ...d, to: e.target.value }))}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="recipient@firm.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
                <input
                  type="text"
                  value={emailData.subject}
                  onChange={(e) => setEmailData((d) => ({ ...d, subject: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setEmailModal(false)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
                <button type="submit" disabled={loading} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg disabled:opacity-60">
                  {loading ? 'Sending…' : 'Send'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Report() {
  const { roomId, reportId } = useParams();
  const { user } = useAuthStore();
  const [report, setReport] = useState(null);
  const [annotations, setAnnotations] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeCitation, setActiveCitation] = useState(null);
  const [activeAnnotationItemId, setActiveAnnotationItemId] = useState(null);
  const [newAnnotation, setNewAnnotation] = useState({ content: '', type: 'comment', itemId: null });
  const [showAnnotationSidebar, setShowAnnotationSidebar] = useState(false);
  const [submittingAnnotation, setSubmittingAnnotation] = useState(false);

  const fetchReport = useCallback(async () => {
    try {
      const data = await reportsApi.get(roomId, reportId);
      setReport(data);
    } catch {}
  }, [roomId, reportId]);

  const fetchAnnotations = useCallback(async () => {
    try {
      const data = await annotationsApi.listByDealRoom(roomId, { page: 1, page_size: 200 });
      setAnnotations(data.annotations ?? {});
    } catch {}
  }, [roomId]);

  useEffect(() => {
    Promise.all([fetchReport(), fetchAnnotations()]).finally(() => setLoading(false));
  }, [fetchReport, fetchAnnotations]);

  usePolling(fetchAnnotations, 15000, true);

  const isApproved = report?.status === 'approved';

  const allAnnotationsList = Object.values(annotations).flat();
  const disputedCount = allAnnotationsList.filter((a) => a.type === 'disputed' && !a.resolved).length;

  const sections = report?.sections ?? [];

  const handleAnnotationClick = (itemId) => {
    setActiveAnnotationItemId(itemId);
    setShowAnnotationSidebar(true);
  };

  const handleAddAnnotation = (section) => {
    const firstItemId = section.items?.[0]?.id;
    setNewAnnotation({ content: '', type: 'comment', itemId: firstItemId });
    setShowAnnotationSidebar(true);
  };

  const handleSubmitAnnotation = async (e) => {
    e.preventDefault();
    if (!newAnnotation.content.trim() || !newAnnotation.itemId) return;
    setSubmittingAnnotation(true);
    try {
      await annotationsApi.create(roomId, {
        report_item_id: newAnnotation.itemId,
        content: newAnnotation.content,
        type: newAnnotation.type,
      });
      setNewAnnotation({ content: '', type: 'comment', itemId: newAnnotation.itemId });
      await fetchAnnotations();
    } catch (err) {
      alert(err.response?.data?.detail ?? 'Failed to post annotation.');
    } finally {
      setSubmittingAnnotation(false);
    }
  };

  if (loading) {
    return (
      <>
        <Topbar breadcrumbs={[{ to: '/', label: 'Dashboard' }, { label: '…' }, { label: 'Report' }]} />
        <main className="flex-1 px-6 py-6"><Skeleton /></main>
      </>
    );
  }

  const activeAnnotations = activeAnnotationItemId ? (annotations[activeAnnotationItemId] ?? []) : [];

  return (
    <>
      <Topbar
        breadcrumbs={[
          { to: '/', label: 'Dashboard' },
          { to: `/deal-rooms/${roomId}`, label: report?.deal_room_name ?? 'Deal Room' },
          { label: 'Report' },
        ]}
      />

      <main className="flex-1 flex overflow-hidden">
        {/* Left: section navigation */}
        <aside className="w-48 shrink-0 border-r border-gray-200 bg-white overflow-y-auto py-4 px-3 hidden lg:block">
          <p className="text-xs text-gray-400 uppercase tracking-wider font-medium mb-3 px-2">Sections</p>
          <nav className="space-y-1">
            {sections.map((s) => {
              const sectionAnnotations = s.items?.flatMap((item) => annotations[item.id] ?? []) ?? [];
              const hasDisputed = sectionAnnotations.some((a) => a.type === 'disputed' && !a.resolved);
              return (
                <a
                  key={s.id ?? s.section_key}
                  href={`#section-${s.section_key ?? s.id}`}
                  className="flex items-center justify-between px-2 py-1.5 rounded-lg text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <span className="truncate">{s.title ?? s.section_key}</span>
                  {hasDisputed && <span className="w-2 h-2 rounded-full bg-red-500 shrink-0 ml-1" />}
                </a>
              );
            })}
          </nav>
        </aside>

        {/* Centre: report content */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {/* Approval bar */}
          <ApprovalBar
            report={report}
            dealRoomId={roomId}
            userRole={user?.role}
            disputedCount={disputedCount}
            onStatusChange={fetchReport}
          />

          {/* Risk score card */}
          {report?.risk_score != null && (
            <RiskScoreCard report={report} />
          )}

          {/* Report sections */}
          {sections.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
              <p className="text-2xl mb-2">📊</p>
              <p className="text-sm">Report is still being generated…</p>
            </div>
          ) : (
            sections.map((section) => (
              <ReportSection
                key={section.id ?? section.section_key}
                section={section}
                dealRoomId={roomId}
                reportId={reportId}
                annotationsByItem={annotations}
                isApproved={isApproved}
                onCitationClick={setActiveCitation}
                onAnnotationClick={handleAnnotationClick}
                onAddAnnotation={handleAddAnnotation}
              />
            ))
          )}

          {/* Q&A Panel */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <QAPanel dealRoomId={roomId} reportId={reportId} />
          </div>
        </div>

        {/* Right: annotation sidebar */}
        <aside className="w-72 shrink-0 border-l border-gray-200 bg-white overflow-y-auto py-4 px-4 hidden xl:flex xl:flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">Annotations</p>
            {disputedCount > 0 && (
              <span className="text-xs font-medium text-red-600">{disputedCount} disputed</span>
            )}
          </div>

          {/* New annotation form */}
          {!isApproved && (
            <form onSubmit={handleSubmitAnnotation} className="space-y-2">
              <select
                value={newAnnotation.type}
                onChange={(e) => setNewAnnotation((a) => ({ ...a, type: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="comment">Comment</option>
                <option value="verified">Verified</option>
                <option value="disputed">Disputed</option>
              </select>
              <textarea
                value={newAnnotation.content}
                onChange={(e) => setNewAnnotation((a) => ({ ...a, content: e.target.value }))}
                placeholder={activeAnnotationItemId ? 'Write annotation…' : 'Select a section item first'}
                disabled={!newAnnotation.itemId}
                rows={3}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={submittingAnnotation || !newAnnotation.itemId || !newAnnotation.content.trim()}
                className="w-full py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs rounded-lg transition-colors"
              >
                {submittingAnnotation ? 'Posting…' : 'Post annotation'}
              </button>
            </form>
          )}

          {activeAnnotations.length > 0 ? (
            <AnnotationThread annotations={activeAnnotations} onResolved={fetchAnnotations} />
          ) : (
            <p className="text-xs text-gray-400 italic">
              {activeAnnotationItemId ? 'No annotations on this item.' : 'Click a section to see annotations.'}
            </p>
          )}
        </aside>
      </main>

      {activeCitation && (
        <CitationPanel citation={activeCitation} onClose={() => setActiveCitation(null)} />
      )}
    </>
  );
}
