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

  const buildSectionProse = (items) => {
    const sentences = items
      .map((item) => (item.edited_content || item.content || '').replace(/\s*\[SOURCE:[^\]]*\]/gi, '').trim())
      .filter(Boolean);

    // Split into paragraphs of ~4 sentences each for readability
    const paragraphs = [];
    for (let i = 0; i < sentences.length; i += 4) {
      paragraphs.push(sentences.slice(i, i + 4).join(' '));
    }

    // Deduplicated sources
    const seen = new Set();
    const sources = [];
    for (const item of items) {
      if (item.citation?.source_name) {
        const key = item.citation.source_name;
        if (!seen.has(key)) {
          seen.add(key);
          sources.push(item.citation);
        }
      }
    }

    return { paragraphs, sources };
  };

  const handleExportPDF = () => {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const company = report?.deal_room_name ?? 'Report';
    const date = report?.created_at ? new Date(report.created_at).toLocaleDateString() : '';
    const pageW = doc.internal.pageSize.getWidth();
    const pageH = doc.internal.pageSize.getHeight();
    const marginL = 62;
    const marginR = 62;
    const contentW = pageW - marginL - marginR;
    let y = 56;

    const checkPage = (needed = 20) => {
      if (y + needed > pageH - 56) { doc.addPage(); y = 56; }
    };

    const writeParagraph = (text, fontSize, color, bold = false, extraGapAfter = 0) => {
      doc.setFontSize(fontSize);
      doc.setTextColor(...color);
      doc.setFont('helvetica', bold ? 'bold' : 'normal');
      const lines = doc.splitTextToSize(text, contentW);
      const lineH = fontSize * 1.55;
      checkPage(lines.length * lineH + extraGapAfter);
      doc.text(lines, marginL, y);
      y += lines.length * lineH + extraGapAfter;
    };

    // ── Cover page ──────────────────────────────────────────────────────────
    doc.setFillColor(26, 94, 58);          // brand green
    doc.rect(0, 0, pageW, 110, 'F');
    doc.setFillColor(212, 168, 75);        // gold rule
    doc.rect(0, 110, pageW, 3, 'F');

    doc.setFontSize(24);
    doc.setTextColor(250, 249, 245);
    doc.setFont('helvetica', 'bold');
    doc.text(company, marginL, 46);
    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    doc.text('Due Diligence Report', marginL, 66);
    doc.setFontSize(10);
    doc.setTextColor(200, 230, 210);
    if (date) doc.text(`Generated: ${date}`, marginL, 88);
    y = 130;

    // Risk score line
    if (report?.risk_score != null) {
      const tier = (report.risk_tier ?? '').toUpperCase();
      const scoreText = `Risk Score: ${report.risk_score} / 100${tier ? `  |  ${tier}` : ''}`;
      doc.setFontSize(10);
      doc.setTextColor(80, 80, 80);
      doc.setFont('helvetica', 'bold');
      doc.text(scoreText, marginL, y);
      y += 22;
    }

    // Horizontal rule
    doc.setDrawColor(212, 168, 75);
    doc.setLineWidth(0.5);
    doc.line(marginL, y, pageW - marginR, y);
    y += 18;

    // ── Sections ─────────────────────────────────────────────────────────────
    for (const section of sections) {
      checkPage(60);

      // Section heading
      doc.setFillColor(245, 248, 245);
      doc.rect(marginL - 10, y - 13, contentW + 20, 22, 'F');
      doc.setFontSize(13);
      doc.setTextColor(26, 94, 58);
      doc.setFont('helvetica', 'bold');
      doc.text(section.title, marginL, y);
      y += 20;

      const { paragraphs, sources } = buildSectionProse(section.items);

      for (const para of paragraphs) {
        writeParagraph(para, 10.5, [30, 30, 30], false, 10);
      }

      // Sources block at end of section
      if (sources.length > 0) {
        y += 4;
        checkPage(30);
        doc.setDrawColor(220, 220, 220);
        doc.setLineWidth(0.3);
        doc.line(marginL, y, marginL + 120, y);
        y += 8;
        const sourceText = 'Sources: ' + sources.map((s) =>
          s.source_name + (s.page_number ? ` (p.${s.page_number})` : '')
        ).join('  ·  ');
        writeParagraph(sourceText, 8, [140, 140, 140], false, 0);
        y += 18;
      } else {
        y += 14;
      }
    }

    // Page numbers
    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(160, 160, 160);
      doc.setFont('helvetica', 'normal');
      doc.text(`${company} — Confidential  |  Page ${i} of ${pageCount}`, marginL, pageH - 28);
    }

    doc.save(`${company.replace(/[^a-z0-9]/gi, '-')}-due-diligence.pdf`);
  };

  const handleExportWord = () => {
    const company = report?.deal_room_name ?? 'Report';
    const date = report?.created_at ? new Date(report.created_at).toLocaleDateString() : '';
    const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

    let html = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8">
<style>
  body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.7; margin: 2.5cm 3cm; color: #1a1a1a; }
  h1 { font-size: 22pt; color: #1a5e3a; margin-bottom: 2pt; border-bottom: 3px solid #d4a84b; padding-bottom: 6pt; }
  h2 { font-size: 13pt; color: #1a5e3a; border-bottom: 1px solid #d4a84b; padding-bottom: 3pt; margin-top: 28pt; margin-bottom: 10pt; }
  p { margin: 0 0 10pt 0; text-align: justify; }
  .meta { color: #666; font-size: 9.5pt; margin-bottom: 4pt; }
  .risk { font-size: 10pt; font-weight: bold; color: #1a5e3a; margin-bottom: 16pt; }
  .sources { color: #888; font-size: 8.5pt; font-style: italic; border-top: 1px solid #e0e0e0; margin-top: 6pt; padding-top: 5pt; }
  .unverified { color: #b45309; }
</style>
</head><body>`;

    html += `<h1>${esc(company)} &mdash; Due Diligence Report</h1>`;
    html += `<p class="meta">Status: ${esc(report?.status ?? '')} &nbsp;&nbsp;|&nbsp;&nbsp; Generated: ${esc(date)}</p>`;
    if (report?.risk_score != null) {
      const tier = report.risk_tier ? ` &mdash; ${report.risk_tier.toUpperCase()}` : '';
      html += `<p class="risk">Risk Score: ${report.risk_score} / 100${tier}</p>`;
    }

    for (const section of sections) {
      html += `<h2>${esc(section.title)}</h2>`;
      const { paragraphs, sources } = buildSectionProse(section.items);

      for (const para of paragraphs) {
        const hasUnverified = section.items.some((it) => !it.is_verified);
        const cls = hasUnverified ? ' class="unverified"' : '';
        html += `<p${cls}>${esc(para)}</p>`;
      }

      if (sources.length > 0) {
        const srcList = sources
          .map((s) => esc(s.source_name) + (s.page_number ? ` (p.${s.page_number})` : ''))
          .join(' &nbsp;&middot;&nbsp; ');
        html += `<p class="sources">Sources: ${srcList}</p>`;
      }
    }

    html += '</body></html>';
    const blob = new Blob(['﻿', html], { type: 'application/msword' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${company.replace(/[^a-z0-9]/gi, '-')}-due-diligence.doc`;
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
