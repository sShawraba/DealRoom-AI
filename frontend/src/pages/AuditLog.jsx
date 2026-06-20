import { useState, useEffect, useCallback } from 'react';
import { list, exportCSV } from '../api/audit';
import Topbar from '../components/layout/Topbar';
import ActivityFeed from '../components/audit/ActivityFeed';
import Pagination from '../components/Pagination';

export default function AuditLog() {
  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ user: '', actions: [], dateFrom: '', dateTo: '' });

  const handleFilterChange = useCallback((updater) => {
    setPage(1);
    setFilters(updater);
  }, []);
  const [exporting, setExporting] = useState(false);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: 50 };
      if (filters.user) params.actor_email = filters.user;
      if (filters.actions.length) params.actions = filters.actions.join(',');
      if (filters.dateFrom) params.date_from = filters.dateFrom;
      if (filters.dateTo) params.date_to = filters.dateTo;
      const data = await list(params);
      setEvents(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to load audit log.');
      setEvents([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const response = await exportCSV({});
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'audit-log.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Export failed — the audit export endpoint may not be available yet.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <Topbar breadcrumbs={[{ to: '/dashboard', label: 'Dashboard' }, { label: 'Audit Log' }]} />

      <main className="flex-1 px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-brand-ink">Audit Log</h2>
            <p className="text-sm text-brand-taupe mt-0.5">{total} events</p>
          </div>
          <button
            onClick={handleExportCSV}
            disabled={exporting}
            className="px-4 py-2 text-sm border border-brand-sand rounded-lg text-brand-ink hover:bg-brand-sand disabled:opacity-60 transition-colors"
          >
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}
        <ActivityFeed events={events} loading={loading} filters={filters} onFilterChange={handleFilterChange} />

        {!loading && total > 50 && (
          <div className="mt-6">
            <Pagination page={page} total={total} pageSize={50} onChange={setPage} />
          </div>
        )}
      </main>
    </>
  );
}
