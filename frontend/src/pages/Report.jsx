import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { jsPDF } from 'jspdf';
import * as reportsApi from '../api/reports';
import * as annotationsApi from '../api/annotations';
import * as managementQAApi from '../api/managementQA';
import * as dealRoomsApi from '../api/dealRooms';
import useAuthStore from '../store/authStore';
import usePolling from '../hooks/usePolling';
import Topbar from '../components/layout/Topbar';
import RiskScoreCard from '../components/report/RiskScoreCard';
import ReportSection from '../components/report/ReportSection';
import ApprovalBar from '../components/report/ApprovalBar';
import CitationPanel from '../components/report/CitationPanel';

const errMsg = (err, fallback) => {
  const d = err.response?.data?.detail;
  if (!d) return fallback;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e) => e.msg ?? JSON.stringify(e)).join(', ');
  return fallback;
};

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
  const [recipientEmail, setRecipientEmail] = useState('');

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
      alert(errMsg(err, 'Failed to generate Q&A.'));
    } finally {
      setGenerating(false);
    }
  };

  const handleSendEmail = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await managementQAApi.sendEmail(dealRoomId, reportId, { recipient_email: recipientEmail });
      setEmailModal(false);
      setRecipientEmail('');
    } catch (err) {
      alert(errMsg(err, 'Failed to send email.'));
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
                <label className="block text-sm font-medium text-gray-700 mb-1">Recipient email</label>
                <input
                  type="email"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="recipient@firm.com"
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
  const [cancelling, setCancelling] = useState(false);
  const [myRoomRole, setMyRoomRole] = useState(null);

  const handleCancel = async () => {
    if (!window.confirm('Cancel this report? This cannot be undone.')) return;
    setCancelling(true);
    try {
      await reportsApi.cancel(roomId, reportId);
      await fetchReport();
    } catch {
      alert('Failed to cancel report.');
    } finally {
      setCancelling(false);
    }
  };

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

  useEffect(() => {
    if (!user?.id) return;
    dealRoomsApi.listMembers(roomId)
      .then((d) => {
        const me = (d.items ?? []).find((m) => m.user_id === user.id);
        setMyRoomRole(me?.role ?? null);
      })
      .catch(() => {});
  }, [roomId, user?.id]);

  const isInProgress = report?.status === 'generating' || report?.status === 'pending' || report?.status === null;
  usePolling(fetchReport, 4000, isInProgress);
  usePolling(fetchAnnotations, 15000, true);

  const isApproved = report?.status === 'approved';

  const handleExportPDF = () => {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const company = report?.deal_room_name ?? 'Report';
    const date = report?.created_at ? new Date(report.created_at).toLocaleDateString() : '';
    const pageW = doc.internal.pageSize.getWidth();
    const marginL = 56;
    const marginR = 56;
    const contentW = pageW - marginL - marginR;
    let y = 56;

    const checkPage = (needed = 20) => {
      if (y + needed > doc.internal.pageSize.getHeight() - 56) {
        doc.addPage();
        y = 56;
      }
    };

    const writeWrapped = (text, fontSize, color, bold = false) => {
      doc.setFontSize(fontSize);
      doc.setTextColor(...color);
      doc.setFont('helvetica', bold ? 'bold' : 'normal');
      const lines = doc.splitTextToSize(text, contentW);
      const lineH = fontSize * 1.45;
      checkPage(lines.length * lineH);
      doc.text(lines, marginL, y);
      y += lines.length * lineH;
    };

    // Cover header
    doc.setFillColor(26, 58, 92);
    doc.rect(0, 0, pageW, 90, 'F');
    doc.setFontSize(22);
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.text(company, marginL, 38);
    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
    doc.text('Due Diligence Report', marginL, 56);
    if (date) doc.text(`Generated: ${date}`, marginL, 72);
    y = 110;

    if (report?.risk_score != null) {
      doc.setFontSize(10);
      doc.setTextColor(100, 100, 100);
      doc.setFont('helvetica', 'normal');
      doc.text(`Risk Score: ${report.risk_score}/10`, marginL, y);
      y += 20;
    }

    for (const section of sections) {
      y += 10;
      checkPage(50);

      // Section heading bar
      doc.setFillColor(240, 245, 255);
      doc.rect(marginL - 8, y - 14, contentW + 16, 22, 'F');
      doc.setFontSize(13);
      doc.setTextColor(26, 58, 92);
      doc.setFont('helvetica', 'bold');
      doc.text(section.title, marginL, y);
      y += 18;

      for (const item of section.items) {
        const text = (item.edited_content || item.content || '').replace(/\s*\[SOURCE:[^\]]*\]/gi, '').trim();
        if (!text) continue;
        y += 6;
        writeWrapped(text, 10, [40, 40, 40]);

        if (item.citation?.source_name) {
          y += 2;
          writeWrapped(
            `Source: ${item.citation.source_name}${item.citation.page_number ? `, p.${item.citation.page_number}` : ''}`,
            8.5,
            [130, 130, 130],
          );
        }
        y += 4;
      }
    }

    const filename = `${company.replace(/[^a-z0-9]/gi, '-')}-due-diligence.pdf`;
    doc.save(filename);
  };

  const handleExportWord = () => {
    const company = report?.deal_room_name ?? 'Report';
    const date = report?.created_at ? new Date(report.created_at).toLocaleDateString() : '';
    let html = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8">
<style>
  body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; margin: 2cm; color: #111; }
  h1 { font-size: 18pt; color: #1a1a2e; margin-bottom: 4pt; }
  h2 { font-size: 13pt; color: #1a3a5c; border-bottom: 1px solid #ccc; padding-bottom: 4pt; margin-top: 20pt; }
  p { margin: 6pt 0; }
  .meta { color: #666; font-size: 9pt; }
  .citation { color: #888; font-size: 9pt; font-style: italic; }
  .unverified { color: #b45309; }
</style>
</head><body>`;
    html += `<h1>${company} — Due Diligence Report</h1>`;
    html += `<p class="meta">Status: ${report?.status ?? ''} &nbsp;|&nbsp; Generated: ${date}</p>`;
    if (report?.risk_score != null) {
      html += `<p class="meta">Risk Score: ${report.risk_score}/10</p>`;
    }

    for (const section of sections) {
      html += `<h2>${section.title}</h2>`;
      for (const item of section.items) {
        const text = (item.edited_content || item.content || '').replace(/\s*\[SOURCE:[^\]]*\]/gi, '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const cls = item.is_verified ? '' : ' class="unverified"';
        html += `<p${cls}>${text}`;
        if (item.edited_by_email) {
          html += ` <span class="citation">(edited by ${item.edited_by_email})</span>`;
        }
        html += `</p>`;
        if (item.citation?.source_name) {
          html += `<p class="citation">Source: ${item.citation.source_name}${item.citation.page_number ? `, p.${item.citation.page_number}` : ''}</p>`;
        }
      }
    }

    html += '</body></html>';
    const blob = new Blob(['﻿', html], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(company).replace(/[^a-z0-9]/gi, '-')}-due-diligence.doc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const allAnnotationsList = Object.values(annotations).flat();
  const disputedCount = allAnnotationsList.filter((a) => a.type === 'disputed' && !a.resolved).length;

  const sections = useMemo(() => {
    if (!report?.items?.length) return [];
    const order = ['executive_summary', 'financial_health', 'commercial_assessment', 'legal_flags', 'red_flags', 'key_questions'];
    const grouped = {};
    for (const item of report.items) {
      const key = item.section_type;
      if (!grouped[key]) {
        grouped[key] = {
          section_key: key,
          title: key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
          items: [],
        };
      }
      grouped[key].items.push(item);
    }
    return order.filter((k) => grouped[k]).map((k) => grouped[k]);
  }, [report?.items]);

  if (loading) {
    return (
      <>
        <Topbar breadcrumbs={[{ to: '/', label: 'Dashboard' }, { label: '…' }, { label: 'Report' }]} />
        <main className="flex-1 px-6 py-6"><Skeleton /></main>
      </>
    );
  }

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

        {/* Centre: report content + sticky approval bar */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 pb-6">
            {/* Risk score card */}
            {report?.risk_score != null && (
              <RiskScoreCard report={report} />
            )}

            {/* Report sections */}
            {sections.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
                <p className="text-2xl mb-2">📊</p>
                <p className="text-sm">
                  {report?.status === 'failed'
                    ? `Failed: ${report.error_message ?? 'Unknown error'}`
                    : 'Report is still being generated…'}
                </p>
                {(report?.status === 'pending' || report?.status === 'running') && (
                  <button
                    onClick={handleCancel}
                    disabled={cancelling}
                    className="mt-4 text-xs px-3 py-1.5 text-red-600 border border-red-300 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
                  >
                    {cancelling ? 'Cancelling…' : 'Cancel report'}
                  </button>
                )}
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
                  onRefreshAnnotations={fetchAnnotations}
                  onItemSaved={fetchReport}
                />
              ))
            )}

            {/* Q&A Panel */}
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <QAPanel dealRoomId={roomId} reportId={reportId} />
            </div>
          </div>

          {/* Sticky approval bar */}
          <ApprovalBar
            report={report}
            dealRoomId={roomId}
            userRole={myRoomRole}
            disputedCount={disputedCount}
            onStatusChange={fetchReport}
            onExportPDF={handleExportPDF}
            onExportWord={handleExportWord}
          />
        </div>
      </main>

      {activeCitation && (
        <CitationPanel citation={activeCitation} onClose={() => setActiveCitation(null)} />
      )}
    </>
  );
}
