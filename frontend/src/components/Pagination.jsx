export default function Pagination({ page, total, pageSize, onChange }) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-3">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 text-sm border border-brand-sand rounded-lg text-brand-ink disabled:opacity-40 hover:bg-brand-sand transition-colors"
      >
        Previous
      </button>
      <span className="text-sm text-brand-taupe">
        Page {page} of {totalPages}
        <span className="ml-2" style={{ color: '#D4D0C4' }}>({total} total)</span>
      </span>
      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 text-sm border border-brand-sand rounded-lg text-brand-ink disabled:opacity-40 hover:bg-brand-sand transition-colors"
      >
        Next
      </button>
    </div>
  );
}
