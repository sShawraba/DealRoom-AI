export default function Pagination({ page, total, pageSize, onChange }) {
  const totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-3">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
      >
        Previous
      </button>
      <span className="text-sm text-gray-600">
        Page {page} of {totalPages}
        <span className="text-gray-400 ml-2">({total} total)</span>
      </span>
      <button
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
      >
        Next
      </button>
    </div>
  );
}
